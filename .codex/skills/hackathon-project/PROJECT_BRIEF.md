# LanGo Project Brief

## Track

Education

## Project Summary

LanGo is a language-learning headset focused on making education more interactive and personal.
The product helps users learn a selected language by pointing at objects, translating text and sound, and practicing through guided game and conversation modes.
The hardware terminal for the prototype will be a Raspberry Pi, which will communicate with a web app that the team plans to build later.

## Core Experience

The user wears a headset and interacts with the real world instead of a static lesson screen.
The system recognizes what the user is looking at or hearing, then responds with translations, prompts, or feedback in the target language.

## Primary Features

### Object Translation

- Point at an object to identify it
- Return the word or translation in the selected language

### Text Translation

- Capture visible text
- Extract and translate the text

### Sound Translation

- Capture speech or audio
- Convert audio to text
- Translate or speak back the result

### Game Mode

- Use a laser pointer to highlight objects in front of the user
- Prompt the user to answer in the chosen language
- Give immediate correctness feedback

### Conversation Mode

- Let the user practice short spoken exchanges
- Provide feedback on response quality

### Memory Cache

- Store recent translations and recognized objects
- Reuse translation history for speed and review

### Mode Switching

- Change modes by voice prompt
- Change modes with a physical button

## Hardware Direction

- Raspberry Pi as the hardware terminal
- Headset form factor around the Raspberry Pi prototype
- Webcam
- Laser pointer
- Motors or servos for pointer control if needed

## Software Direction

### Primary Language

- Python is the primary implementation language

### Backend Responsibilities

- Raspberry Pi device control
- Computer vision pipeline
- Object detection with YOLO models
- Speech-to-text
- Text-to-speech
- Translation logic
- Translation-history caching
- Device mode management

### Planned Services And Tools

- YOLO for CV/object recognition
- STT and TTS pipeline
- Groq for speech or language-processing components if useful

## Team Needs

### Hardware Professionals

- Integrate webcam, pointer, motors, and headset hardware
- Handle prototyping, wiring, and reliability
- Make the build stable enough for a live demo

### Frontend Professionals

- Design and build the web app
- Present translations, prompts, and feedback clearly
- Support a clean demo flow for judges and users

## Design Workflow

- Use Figma for flows, wireframes, and mockups
- Design the Raspberry Pi to web app interaction flow before implementation
- Keep the user journey simple enough for a hackathon demo

## Demo Priorities

- One clear end-to-end language-learning loop
- Clear communication between the Raspberry Pi terminal and the web app
- A working object, text, or sound translation flow
- A working game mode or conversation mode
- Strong hardware/software integration in the demo

## Open Questions

- Which language pair should the first demo support
- Which feature should be the primary judging demo
- How much conversation feedback is realistic within hackathon scope
