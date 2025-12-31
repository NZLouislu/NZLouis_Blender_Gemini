# NZLouis Blender Gemini Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Blender-4.0%2B-orange" alt="Blender Version">
  <img src="https://img.shields.io/badge/Gemini-3.0%20Flash-blue" alt="Gemini Version">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

**NZLouis Blender Gemini Assistant** is a next-generation AI copilot for Blender, powered by Google's latest **Gemini 3.0 Flash**. 

Designed for **Digital Twins**, **Architectural Visualization**, and **Robotics Simulation** workflows, this tool allows you to control Blender using natural language, execute Python scripts automatically, and accelerate your 3D creation process.

> **Attribution**: This project is based on the original `Blender_Gemini_MCP` addon by Gabriel Netto, licensed under MIT. It has been significantly enhanced by Louis with Gemini 3.0 support and workflow optimizations.

## ✨ Key Features

- **🧠 Powered by Gemini 3.0**: Leverages the newest `gemini-3-flash-preview` (Dec 2025) for superior reasoning logic and complex script generation.
- **🤖 Digital Twin Ready**: Optimized system prompts for scene construction, object manipulation, and procedural generation.
- **🔌 Smart Connection**: Built-in connection tester and multi-model fallback (Gemini 3.0 -> 2.5 -> 2.0).
- **🔐 Secure & Professional**: Supports `.env` file configuration for secure API key management in professional environments.
- **⚡ Non-Blocking UI**: Asynchronous execution ensures Blender never freezes while the AI is thinking.

## 📥 Installation

### 1. Install the Addon
1. Download the repository as a **ZIP** file.
2. Open Blender → `Edit` → `Preferences` → `Add-ons`.
3. Click **Install...** and select the ZIP file.
4. Enable the **"NZLouis Blender Gemini Assistant"** addon.

### 2. Install Dependencies
You must install the `google-generativeai` library into Blender's Python environment.

**Windows:**
Run CMD as Administrator:
```bash
"C:\Program Files\Blender Foundation\Blender 4.0\4.0\python\bin\python.exe" -m pip install google-generativeai
```

**macOS/Linux:**
```bash
/path/to/blender/python/bin/python3.11 -m pip install google-generativeai
```

## 🚀 Usage

### 1. Configure
- Go to Add-on Preferences.
- Enter your [Google API Key](https://aistudio.google.com/app/apikey) (or use a `.env` file).
- Click the **Test Connection (✓)** button.

### 2. Create
- Press **N** in the 3D Viewport to open the sidebar.
- Navigate to the **"NZLouis Gemini"** tab.
- Enter a prompt, e.g.:
  > "Create a 10x10 grid of city buildings with random heights and apply a concrete material."
- Click **Execute Code** and watch your scene build itself.

### 3. Quick Access
- Press **Alt + G** anywhere to bring up the quick prompt window.

## 🗺️ Roadmap & Vision

We are building the future of AI-assisted 3D creation.
- [x] Gemini 3.0 Integration
- [x] Connection Diagnostics
- [ ] Context-Aware Scene Reading (Coming Soon)
- [ ] Automated Error Correction Loop
- [ ] Robotics Simulation Presets

## 📄 License

This project is licensed under the **MIT License**. You are free to fork, modify, and distribute it.
