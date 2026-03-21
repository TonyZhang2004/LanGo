# LanGo System Design

## Overview

LanGo is an education-focused language-learning headset that combines computer vision, speech processing, and a companion web app to create a more interactive learning experience.
For the prototype, a Raspberry Pi acts as the hardware terminal and communicates with the web app.

The system supports:

- object translation
- text translation
- sound translation
- game mode with laser-guided prompts
- conversation mode with spoken feedback
- translation-history caching

Python is the primary implementation language for the core system.

## Goals

- Build a clear hackathon demo with one end-to-end learning loop
- Show real-world interaction through headset hardware
- Keep architecture modular enough to expand after the hackathon
- Support both hardware integration and a polished frontend demo

## Non-Goals

- Full production-grade wearable hardware
- Perfect conversation scoring or pronunciation grading
- Broad multilingual support on day one
- Fully offline inference for every subsystem

## High-Level Architecture

```text
[User]
  |
  v
[Headset Hardware / Raspberry Pi Terminal]
  |- webcam
  |- microphone
  |- button input
  |- laser pointer
  |- optional motors/servos
  |
  v
[Python Raspberry Pi Controller]
  |- mode manager
  |- capture orchestration
  |- cache client
  |- webapp client
  |
  +------------------------------+
  |                              |
  v                              v
[Vision Pipeline]           [Audio Pipeline]
  |- object detection          |- speech-to-text
  |- OCR / text extraction     |- text-to-speech
  |- target selection          |- conversation capture
  |                              |
  +---------------+--------------+
                  |
                  v
          [Language Service]
            |- translation
            |- prompt generation
            |- answer evaluation
            |- conversation feedback
                  |
                  v
          [Cache / Session Store]
                  |
                  v
         [Frontend / Web App]
            |- translation results
            |- session history
            |- game prompts
            |- mode controls
```

## Major Components

### 1. Headset Hardware

Responsibilities:

- run on Raspberry Pi as the device terminal
- capture image frames from the webcam
- capture user speech
- let the user switch modes with a button
- point to objects using a laser
- optionally move the laser with motors or servos

Notes:

- for the hackathon, reliability matters more than miniaturization
- a bench-top or mounted prototype is acceptable if the flow is clear

### 2. Python Device Controller

Responsibilities:

- run the main on-device process on Raspberry Pi
- coordinate all hardware input and output
- track active mode
- trigger image or audio capture
- call backend services
- send results to the web app

Suggested modules:

- `device_controller.py`
- `mode_manager.py`
- `webapp_client.py`
- `hardware/`
- `services/`

### 3. Vision Pipeline

Responsibilities:

- detect objects from webcam frames with YOLO
- identify the object the user is pointing at
- extract text when text translation mode is active

Suggested subcomponents:

- object detector
- OCR extractor
- target resolver for laser/object alignment

Inputs:

- image frames
- current mode
- optional pointer coordinates

Outputs:

- detected object label
- extracted text
- confidence score

### 4. Audio Pipeline

Responsibilities:

- capture speech from the user
- convert speech to text
- speak translations or feedback back to the user

Suggested subcomponents:

- microphone capture
- STT service adapter
- TTS service adapter

Inputs:

- live or recorded audio

Outputs:

- transcript
- audio response

### 5. Language Service

Responsibilities:

- translate objects, text, and spoken content
- generate quiz prompts for game mode
- evaluate answers in the selected language
- produce simple conversation feedback

Notes:

- Groq-backed models or APIs can be used where they help speed of implementation
- response latency matters for demo quality

### 6. Cache And Session Store

Responsibilities:

- save recent translations
- store recognized objects and prior answers
- support quick lookups for repeated interactions
- preserve lightweight session history for the frontend

Hackathon recommendation:

- start with in-memory Python structures or SQLite
- move to Redis only if latency or concurrency requires it

### 7. Frontend / Companion App

Responsibilities:

- receive results from the Raspberry Pi terminal
- show current mode
- display translation results
- show recognized objects or extracted text
- surface game prompts and feedback
- show translation history

Design workflow:

- define flows and screens in Figma first
- implement from Figma after the core interaction loop is settled

Possible stack:

- lightweight web frontend
- Python backend API for Raspberry Pi and browser communication

## Core User Flows

### Object Translation Flow

1. User switches to object mode.
2. Raspberry Pi captures a frame from the webcam.
3. Vision pipeline identifies the target object.
4. Language service translates the object label.
5. Result is spoken and sent to the web app.
6. Translation is stored in cache/history.

### Text Translation Flow

1. User switches to text mode.
2. Raspberry Pi captures text in view.
3. OCR extracts the text.
4. Language service translates it.
5. Web app displays original and translated text.
6. Optional TTS reads the translation aloud.

### Sound Translation Flow

1. User speaks or captures nearby speech.
2. Raspberry Pi audio pipeline converts speech to text.
3. Language service translates the transcript.
4. Web app displays the result.
5. TTS optionally reads the translation back.

### Game Mode Flow

1. Raspberry Pi system highlights an object with the laser pointer.
2. User is prompted to name the object in the target language.
3. Audio pipeline captures the answer.
4. Language service evaluates the response.
5. Web app shows correctness feedback and score.

### Conversation Mode Flow

1. Raspberry Pi system provides a prompt in the target language.
2. User responds verbally.
3. Audio pipeline transcribes the response.
4. Language service produces simple feedback.
5. Web app shows transcript and feedback summary.

## Mode Management

Supported modes:

- object translation
- text translation
- sound translation
- game mode
- conversation mode

Mode switching options:

- physical button
- spoken mode-switch command

The mode manager should be the single source of truth for active behavior.

## APIs And Interfaces

Suggested internal Python interfaces:

- `capture_frame() -> Frame`
- `capture_audio() -> AudioChunk`
- `detect_object(frame) -> DetectionResult`
- `extract_text(frame) -> str`
- `transcribe(audio) -> str`
- `translate(text, source_lang, target_lang) -> TranslationResult`
- `speak(text, lang) -> AudioResponse`
- `evaluate_answer(prompt, answer, target_lang) -> EvaluationResult`
- `save_history(event) -> None`

Suggested frontend API endpoints:

- `POST /api/mode`
- `POST /api/translate/object`
- `POST /api/translate/text`
- `POST /api/translate/sound`
- `POST /api/game/answer`
- `POST /api/conversation/respond`
- `GET /api/history`

Suggested Raspberry Pi to web app communication:

- Raspberry Pi sends translation and state updates to backend API endpoints
- Web app polls or subscribes for session updates
- Use HTTP first for hackathon simplicity; add WebSocket only if real-time updates become necessary

## Data Model

Suggested entities:

### Session

- session_id
- active_mode
- source_language
- target_language
- created_at

### Translation Event

- event_id
- session_id
- event_type
- input_text
- detected_object
- translated_text
- confidence
- created_at

### Game Attempt

- attempt_id
- session_id
- prompt_object
- expected_answer
- user_answer
- evaluation
- created_at

## MVP Recommendation

Hackathon MVP:

- one supported language pair
- Raspberry Pi as the single device terminal
- object translation from webcam frames
- one simple game mode
- translation history in a lightweight cache
- minimal web app based on Figma screens

Nice-to-have if time remains:

- OCR-based text translation
- sound translation
- conversation mode
- motorized laser alignment

## Risks

- object detection accuracy may be inconsistent in cluttered scenes
- OCR quality depends on lighting and camera angle
- speech latency can hurt demo flow
- laser/object alignment may be difficult without calibration
- conversation scoring can become too ambitious for hackathon scope

## Recommended Build Order

1. Finalize Figma flow for the core demo.
2. Set up Raspberry Pi device control and web app communication.
3. Implement Python mode manager and basic service structure.
4. Integrate webcam capture and YOLO object detection.
5. Add translation and TTS for object mode.
6. Add history caching and simple web app display.
7. Add laser-guided game mode.
8. Add OCR, sound translation, or conversation mode if time remains.
