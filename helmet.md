# Concussion Detection Helmet – Architecture Diagram

```mermaid
graph TD
    %% Styling
    classDef hardware fill:#E6F7FF,stroke:#0099CC,stroke-width:2px,color:#003366;
    classDef software fill:#FFF5E6,stroke:#FF9933,stroke-width:2px,color:#663300;
    classDef ui fill:#F0FFE6,stroke:#33CC33,stroke-width:2px,color:#003300;
    classDef comm fill:#FBEFFF,stroke:#A64DFF,stroke-width:2px,color:#330066;
    classDef power fill:#FFF0F0,stroke:#FF4D4D,stroke-width:2px,color:#660000;

    %% Hardware Layer
    A[Helmet Assembly]:::hardware --> B[MYOSA Mini IoT Board (ESP32)]:::hardware
    B --> C[MPU6050 Sensor (Accel + Gyro)]:::hardware
    B --> D[Buzzer / LED Indicator]:::hardware
    B --> E[Battery + Charging Circuit]:::power

    %% Communication Layer
    B -->|Wi-Fi (MQTT / HTTP)| F[Cloud Server]:::comm

    %% Software Layer
    F --> G[Python Processing Script]:::software
    G --> H[Database (Firebase / MongoDB)]:::software
    G --> I[Concussion Detection Algorithm]:::software

    %% User Interface Layer
    H --> J[Medic Dashboard / Mobile App]:::ui
    J -->|Alert Notification| K[On-field Medic]:::ui

    %% Legends
    subgraph Legend
        L1[Hardware Components]:::hardware
        L2[Communication Links]:::comm
        L3[Software Modules]:::software
        L4[User Interface]:::ui
        L5[Power System]:::power
    end
