# Fish Audio for Home Assistant

Custom integration for Fish Audio Cloud text-to-speech on Home Assistant Core 2025.11.x.

This integration uses the official Fish Audio API:

- `GET https://api.fish.audio/model` to list available voices
- `POST https://api.fish.audio/v1/tts` to generate audio
- `WSS https://api.fish.audio/v1/tts/live` for streaming TTS

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `Fish Audio`.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration** and search for **Fish Audio**.

### Manual

Copy `custom_components/fish_audio` into your Home Assistant `custom_components` directory and restart Home Assistant.

## API Key

Create an API key in your Fish Audio account:

https://fish.audio/app/api-keys/

During setup Home Assistant asks only for the API key and validates it against Fish Audio.

## Configuration

After setup, open **Configure** on the Fish Audio integration to change:

- Voice
- Model
- Language
- Speed
- Pitch
- Volume
- Streaming
- Audio format
- Latency
- Sample rate

You do not need to remove and re-add the integration to change these settings.

## TTS Example

```yaml
service: tts.speak
target:
  entity_id: tts.fish_audio
data:
  message: "Ola mundo"
```

## Automation Example

```yaml
alias: Fish Audio welcome
triggers:
  - trigger: state
    entity_id: binary_sensor.front_door
    to: "on"
actions:
  - action: tts.speak
    target:
      entity_id: tts.fish_audio
    data:
      media_player_entity_id: media_player.living_room
      message: "A porta da frente foi aberta."
```

## Script Example

```yaml
fish_audio_say:
  alias: Fish Audio say
  fields:
    message:
      required: true
  sequence:
    - action: tts.speak
      target:
        entity_id: tts.fish_audio
      data:
        media_player_entity_id: media_player.office
        message: "{{ message }}"
```

## Assist

Fish Audio exposes a standard Home Assistant TTS entity, so it can be selected as the text-to-speech engine for Assist voice pipelines.

1. Go to **Settings > Voice assistants**.
2. Edit or create a pipeline.
3. Select **Fish Audio** as the text-to-speech engine.

## Cache

Generated audio is cached under Home Assistant's config directory in `fish_audio/`.
The cache key uses SHA256 over the synthesis request so repeated messages reuse existing audio.

Clear cached files from Developer Tools:

```yaml
service: fish_audio.clear_cache
```

## Screenshots

![Fish Audio setup](docs/screenshots/setup.png)

![Fish Audio options](docs/screenshots/options.png)

## Troubleshooting

- `invalid_auth`: create a new Fish Audio API key and reconfigure the integration.
- `cannot_connect`: check Fish Audio status and your Home Assistant internet access.
- Rate limits: the integration retries `429` and server errors with exponential backoff, and also applies a conservative local request limit.

## Development

```bash
python -m pip install -r requirements_dev.txt
ruff check .
black --check .
mypy custom_components/fish_audio
```

## License

MIT

