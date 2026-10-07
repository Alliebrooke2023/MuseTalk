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
