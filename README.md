# ✈️ Trip Planner AI

An AI-powered travel planning application that helps users generate personalized travel itineraries using Google Gemini AI. The application allows users to create accounts, chat with an AI assistant, save travel plans, upload trip images, and organize travel memories.

---

## Features

- 🤖 AI-powered travel planning using Google Gemini
- 🗺️ Personalized trip itinerary generation
- 🔐 User authentication (Login & Signup)
- 💬 Interactive AI chat interface
- 💾 Save and manage travel plans
- 🖼️ Upload and organize travel images
- 🧠 AI-based image classification
- 📂 Trip history management
- 🗄️ SQLite database integration
- ⚡ REST API built with FastAPI

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Google Gemini API
- Pillow
- Pydantic

### Frontend

- HTML5
- CSS3
- JavaScript

---

## Project Structure

```
travel-planner-ai/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html
│   └── login.html
│
├── screenshots/
│
├── README.md
├── LICENSE
└── .gitignore
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/travel-planner-ai.git
```

### 2. Navigate to the backend

```bash
cd backend
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a `.env` file

```
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Start the backend server

```bash
uvicorn main:app --reload
```

The backend will run at:

```
http://localhost:8000
```

### 6. Open the frontend

Open `frontend/login.html` in your browser.

---

## Screenshots

Screenshots of the application are available in the **screenshots** folder.

---

## Future Improvements

- Google Maps integration
- Weather forecasting
- Hotel recommendation system
- Flight search integration
- Budget estimation
- Multi-language support
- PDF itinerary export
- Cloud database deployment

---

## License

This project is licensed under the MIT License.
