# voxbridge

YAML-driven config hub. Plug MuseTalk and other models (TTS, STT, LLM) into pipelines.

## Add a model
Drop `configs/models/<name>.yaml`: `name`, `kind`, `command` (with `{placeholders}`), optional `defaults`.

## Add a pipeline
Drop `configs/pipelines/<name>.yaml`. Each step names a model, its `args`, and `outputs` that later steps can use.

## Run
```
pip install -r requirements.txt
python -m hub.cli list
python -m hub.cli run talking_avatar --set text="Hello" --dry-run
python -m pytest tests
```
Run from the `voxbridge` folder. Commands execute from your current directory, so run real pipelines from the MuseTalk root.

## Swarm
Each bot is `configs/agents/<name>.yaml`; a stack in `configs/stacks/` lists them.
`python -m hub.cli swarm chief_of_staff` prints one spawn request per bot (each gets its own container).

## Speech-to-speech
- `sts_chat`: speech -> Whisper -> Claude -> edge-tts speech.
- `sts_avatar`: same, then MuseTalk lip-syncs a video to the reply.
- `voice_convert`: direct voice conversion with Seed-VC.

Run from the MuseTalk root:
```
python -m voxbridge.hub.cli run sts_avatar --set audio_in=question.wav
python -m voxbridge.hub.cli run voice_convert --set audio_in=me.wav --set voice_ref=target.wav
```
Needs: `openai-whisper`, `edge-tts`, `anthropic` + `ANTHROPIC_API_KEY`, MuseTalk weights, and a Seed-VC clone for `voice_convert`.
