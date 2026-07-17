# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

MuseTalk is a real-time audio-driven lip-syncing model. It operates in the latent space of a frozen `ft-mse-vae` (Stable Diffusion VAE), with audio encoded by a frozen `whisper-tiny` model and fused into a UNet (architecture borrowed from `stable-diffusion-v1-4`) via cross-attention. It is **not** a diffusion model — it performs single-step latent inpainting of the lower half of a 256x256 face crop.

Two model versions coexist in this repo and are selected via a `--version` flag (`v1` or `v15`) throughout the scripts:
- **v1.0** (`models/musetalk`): original release, uses a user-tunable `bbox_shift` to control mouth openness.
- **v1.5** (`models/musetalkV15`, recommended): trained with perceptual/GAN/sync loss, two-stage training, fixed `bbox_shift=0`, adds `extra_margin` and cheek-width parsing parameters instead.

Pretrained weights are not checked into the repo — they must be downloaded into `./models/` (see `download_weights.sh`/`.bat`) before any inference or training script will run.

## Common commands

There is no build step, linter, or test suite configured in this repo (no CI config, no pytest/test files besides a manual `test_ffmpeg.py` sanity check). Development is driven entirely through the scripts below.

### Environment setup
```bash
conda create -n MuseTalk python==3.10
conda activate MuseTalk
pip install -r requirements.txt
# MMLab stack (required for training/preprocessing face pose, not for inference)
pip install --no-cache-dir -U openmim
mim install mmengine "mmcv==2.0.1" "mmdet==3.1.0" "mmpose==1.1.0"
```
FFmpeg must be on `PATH`, or pass `--ffmpeg_path` / set `FFMPEG_PATH` — every entrypoint calls `fast_check_ffmpeg()` and shells out to `ffmpeg` directly for frame extraction and video muxing.

### Inference
```bash
# Preferred wrapper (Linux) — picks paths/version flags for you
sh inference.sh v1.5 normal      # single-pass inference, configs/inference/test.yaml
sh inference.sh v1.5 realtime    # avatar-based realtime pipeline, configs/inference/realtime.yaml

# Equivalent direct invocations (needed on Windows, or to override paths)
python -m scripts.inference --inference_config configs/inference/test.yaml \
    --result_dir results/test --unet_model_path models/musetalkV15/unet.pth \
    --unet_config models/musetalkV15/musetalk.json --version v15

python -m scripts.realtime_inference --inference_config configs/inference/realtime.yaml \
    --unet_model_path models/musetalkV15/unet.pth --unet_config models/musetalkV15/musetalk.json \
    --version v15 --fps 25
```
For v1.0, swap `models/musetalkV15` -> `models/musetalk`, `unet.pth` -> `pytorch_model.bin`, `--version v15` -> `--version v1`. `--use_saved_coord` reuses a cached `<video>.pkl` of face landmarks/bboxes instead of recomputing them.

### Training
```bash
python -m scripts.preprocess --config ./configs/training/preprocess.yaml   # extract frames, landmarks, audio features
sh train.sh stage1     # stage1.yaml — random-init UNet
sh train.sh stage2     # stage2.yaml — requires random_init_unet: False, resumes from stage1 checkpoint
```
`train.sh` wraps `accelerate launch --config_file ./configs/training/gpu.yaml train.py --config ./configs/training/<stage>.yaml`. Edit `configs/training/gpu.yaml` (`gpu_ids`, `num_processes`) to match hardware before launching. Stage-specific batch size / gradient accumulation / `n_sample_frames` live in `stage1.yaml` and `stage2.yaml`.

### Gradio demo
```bash
python app.py --use_float16 --ffmpeg_path <path-to-ffmpeg-bin>
```

## Architecture

### Inference data flow (`scripts/inference.py`, `scripts/realtime_inference.py`)
1. `musetalk.utils.utils.load_all_model` loads the VAE (`musetalk/models/vae.py`), UNet (`musetalk/models/unet.py`, a `diffusers.UNet2DConditionModel` with weights loaded from the version-specific checkpoint + `musetalk.json` config), and a sinusoidal `PositionalEncoding` used to project Whisper audio embeddings.
2. `musetalk.utils.audio_processor.AudioProcessor` extracts Whisper features from the input audio and chunks them per-video-frame (`get_whisper_chunk`, using `audio_padding_length_left/right`).
3. `musetalk.utils.preprocessing.get_landmark_and_bbox` runs face detection/landmarking to get a crop bbox per frame; frames are cropped to 256x256 and encoded to latents via `vae.get_latents_for_unet`.
4. `musetalk.utils.utils.datagen` batches (whisper_chunk, latent) pairs; the UNet predicts latents conditioned on audio (cross-attention), the VAE decodes them back to pixel space.
5. `musetalk.utils.blending.get_image`/`get_image_blending` paste the generated mouth region back into the original frame using a face-parsing mask (`musetalk/utils/face_parsing/`), then ffmpeg muxes frames + original audio into the output video.

The **realtime** path (`scripts/realtime_inference.py`) restructures this around a persistent `Avatar` object: face detection/latent extraction ("preparation") happens once per avatar and is cached to disk (`coords.pkl`, `latents.pt`, `mask_coords.pkl`, full frame PNGs under `results/<version>/avatars/<avatar_id>/`), so subsequent calls with new audio only run the UNet/VAE/blending steps (frame consumer runs on a separate thread reading off a `queue.Queue` fed by the generation loop). Set `preparation: True` in `configs/inference/realtime.yaml` only when (re)building an avatar; the bbox_shift stored in `avator_info.json` is compared against the new run's and forces a rebuild if changed.

### Training data flow (`train.py`, `musetalk/utils/training_utils.py`, `musetalk/data/`)
- `initialize_models_and_optimizers` / `initialize_dataloaders` / `initialize_loss_functions` / `initialize_syncnet` / `initialize_vgg` in `musetalk/utils/training_utils.py` assemble everything `train.py`'s loop needs; `train.py` itself is the `accelerate`-driven loop (gradient accumulation, checkpointing via `save_models`/`delete_additional_ckpt`, tensorboard logging).
- `musetalk/data/dataset.py`'s `FaceDataset` reads video (mp4/gif/frame-folder) + precomputed landmark/audio metadata; `musetalk/data/sample_method.py` implements the frame-sampling strategy (e.g. `pose_similarity_and_mouth_dissimilarity`, configured via `data.sample_method` in the stage YAMLs).
- Loss terms (`musetalk/loss/`): `basic_loss.py` (L1/VGG/feature-matching, weighted per `loss_params` in the stage config), `discriminator.py` (GAN loss), `syncnet.py` (lip-sync loss using a separate SyncNet checkpoint, config in `configs/training/syncnet.yaml`), `vgg_face.py` (perceptual loss network).
- Stage1 vs Stage2 is purely a config difference: stage1 trains from a random-init UNet on single sampled frames (`n_sample_frames: 1`); stage2 continues from the stage1 checkpoint (`random_init_unet: False`) with multi-frame sampling (`n_sample_frames: 16`) for temporal consistency, at much higher memory cost — see the GPU memory tables in `README.md` when adjusting `train_bs`/`gradient_accumulation_steps`.

### Supporting subsystems
- `musetalk/whisper/`: a vendored/modified copy of OpenAI Whisper (used only for feature extraction, not transcription) — audio conditioning encoder.
- `musetalk/utils/face_detection/`: S3FD-based face detector (`detection/sfd/`).
- `musetalk/utils/dwpose/`: mmpose config for DWPose landmark model, used by `scripts/preprocess.py`'s `AnalyzeFace` (this is why `mmcv`/`mmpose`/`mmdet` are only needed for training/preprocessing, not plain inference).
- `musetalk/utils/face_parsing/`: BiSeNet-based face parsing, used to build blending masks so only the generated mouth/jaw region overwrites the original frame.
- Both `v1` and `v15` code paths run through the *same* scripts/classes — version-specific behavior is branched inline on `args.version == "v15"` (bbox handling, `extra_margin`, `parsing_mode`, cheek-width args) rather than separate modules. When touching inference/realtime logic, grep for `args.version` to find every branch that needs updating for both versions.

### Configs (`configs/`)
- `configs/inference/test.yaml`, `realtime.yaml`: per-task/per-avatar input definitions (video_path, audio_path(s), optional bbox_shift/result_name).
- `configs/training/gpu.yaml`: `accelerate` launch config (GPU ids, process count).
- `configs/training/preprocess.yaml`, `stage1.yaml`, `stage2.yaml`, `syncnet.yaml`: preprocessing and two-stage training hyperparameters.

### Directory layout
- `models/` (gitignored, user-downloaded): all pretrained checkpoints — `musetalk/`, `musetalkV15/`, `sd-vae/`, `whisper/`, `dwpose/`, `face-parse-bisent/`, `syncnet/`.
- `data/video/`, `data/audio/`: sample inputs referenced by the default inference configs.
- `results/`: inference output videos and intermediate frames/avatar caches (gitignored, created at runtime).
