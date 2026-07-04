from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from dotenv import load_dotenv
import base64
import json
import re
from PIL import Image
import io
import hashlib       
import secrets 
import os

# Database Setup - SQLite (no installation needed)
DATABASE_URL = "sqlite:///./travel_chatbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class TripPlan(Base):
    __tablename__ = "trip_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    trip_name = Column(String(255), index=True)
    destination = Column(String(255))
    plan_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TripImage(Base):
    __tablename__ = "trip_images"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    trip_name = Column(String(255), index=True)
    image_data = Column(LargeBinary)
    image_name = Column(String(255))
    category = Column(String(100))
    tags = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String(255), index=True)
    role = Column(String(50))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="Smart Travel Planning Chatbot")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"
    user_id: str = "demo_user"

class ImageStorage(BaseModel):
    trip_name: str
    images: List[str]

class TripQuery(BaseModel):
    trip_name: str

load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Replace with your actual API key

# Configure Gemini (with error handling)
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Use Gemini 2.5 Flash (fastest and most efficient)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    print("✅ Gemini API configured successfully with gemini-2.5-flash")
except Exception as e:
    print(f"❌ Error configuring Gemini API: {e}")
    model = None

# ML Image Classification Function
def classify_image(image_data: bytes) -> dict:
    """Classify image using Gemini Vision API"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Use Gemini 2.5 Flash for image analysis (supports multimodal)
        vision_model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = """Analyze this travel image and provide:
        1. Main category (beach, mountain, city, food, cultural, adventure, nature)
        2. 3-5 relevant tags
        
        Respond in JSON format:
        {
            "category": "category_name",
            "tags": ["tag1", "tag2", "tag3"]
        }"""
        
        response = vision_model.generate_content([prompt, image])
        
        # Parse response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*|\s*```', '', response_text)
        result = json.loads(response_text)
        
        return result
    except Exception as e:
        print(f"Image classification error: {e}")
        return {"category": "general", "tags": ["travel", "memory"]}

# Helper functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(plain_password) == hashed_password

def generate_token() -> str:
    """Generate a simple session token"""
    return secrets.token_urlsafe(32)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Extract storage command from message
def extract_storage_command(message: str) -> Optional[str]:
    """Extract trip name from storage commands"""
    patterns = [
        r'store.*?(?:with|as|named?)\s+["\']?([^"\']+)["\']?',
        r'save.*?(?:with|as|named?)\s+["\']?([^"\']+)["\']?',
        r'remember.*?(?:with|as|named?)\s+["\']?([^"\']+)["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            return match.group(1).strip()
    return None

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Smart Travel Planning Chatbot API with User Authentication"}

@app.post("/signup")
async def signup(request: SignupRequest):
    """Register a new user"""
    db = next(get_db())
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = hash_password(request.password)
        new_user = User(
            name=request.name,
            email=request.email,
            password_hash=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "Account created successfully",
            "user_id": new_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup error: {str(e)}")

@app.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    db = next(get_db())
    
    try:
        # Find user
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate token
        token = generate_token()
        
        return {
            "message": "Login successful",
            "token": token,
            "user_id": user.id,
            "name": user.name,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/chat")
async def chat(chat_msg: ChatMessage):
    """Handle chat messages and trip planning"""
    db = next(get_db())
    
    try:
        # Check if Gemini is configured
        if model is None:
            raise HTTPException(
                status_code=500, 
                detail="Gemini API not configured. Please check your API key."
            )
        
        # Save user message to history
        user_history = ChatHistory(
            user_id=int(chat_msg.user_id) if chat_msg.user_id != "demo_user" else 0,
            session_id=chat_msg.session_id,
            role="user",
            content=chat_msg.message
        )
        db.add(user_history)
        db.commit()
        
        # Check if it's a storage command
        trip_name = extract_storage_command(chat_msg.message)
        
        if trip_name:
            response_text = f"Great! I'm ready to store images for '{trip_name}'. Please upload the images you want to associate with this trip. You can use the image upload feature in the chat interface."
            has_storage_command = True
        else:
            # Get chat history for context
            history = db.query(ChatHistory).filter(
                ChatHistory.session_id == chat_msg.session_id
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
            
            # Build context
            context = "\n".join([f"{h.role}: {h.content}" for h in reversed(history)])
            
            # Create enhanced prompt for trip planning
            enhanced_prompt = f"""You are a smart travel planning assistant. Help users plan their trips with detailed itineraries, recommendations, and tips.

Previous conversation:
{context}

User: {chat_msg.message}

Provide helpful travel advice, create itineraries, suggest destinations, and help with trip planning. Be conversational and friendly. If the user asks to store or save images, acknowledge that and ask them to upload images through the interface."""
            
            try:
                # Get response from Gemini
                response = model.generate_content(enhanced_prompt)
                response_text = response.text
            except Exception as gemini_error:
                print(f"Gemini API Error: {gemini_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error communicating with Gemini API: {str(gemini_error)}"
                )
            
            has_storage_command = False
        
        # Save assistant response to history
        assistant_history = ChatHistory(
            user_id=int(chat_msg.user_id) if chat_msg.user_id != "demo_user" else 0,
            session_id=chat_msg.session_id,
            role="assistant",
            content=response_text
        )
        db.add(assistant_history)
        db.commit()
        
        return {
            "response": response_text,
            "has_storage_command": has_storage_command,
            "trip_name": trip_name if trip_name else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/upload-images")
async def upload_images(
    trip_name: str = Form(...),
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Upload and classify images for a trip"""
    db = next(get_db())
    
    try:
        uid = int(user_id) if user_id != "demo_user" else 0
        stored_images = []
        
        for file in files:
            # Read image data
            image_data = await file.read()
            
            # Classify image using ML
            classification = classify_image(image_data)
            
            # Store in database
            trip_image = TripImage(
                user_id=uid,
                trip_name=trip_name,
                image_data=image_data,
                image_name=file.filename,
                category=classification.get("category", "general"),
                tags=",".join(classification.get("tags", []))
            )
            db.add(trip_image)
            
            stored_images.append({
                "filename": file.filename,
                "category": classification.get("category"),
                "tags": classification.get("tags")
            })
        
        db.commit()
        
        return {
            "message": f"Successfully stored {len(files)} images for trip '{trip_name}'",
            "images": stored_images
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Image upload error: {str(e)}")

@app.post("/save-trip-plan")
async def save_trip_plan(trip_name: str = Form(...), destination: str = Form(...), plan_details: str = Form(...), user_id: str = Form(...)):
    """Save a complete trip plan"""
    db = next(get_db())
    
    try:
        uid = int(user_id) if user_id != "demo_user" else 0
        trip_plan = TripPlan(
            user_id=uid,
            trip_name=trip_name,
            destination=destination,
            plan_details=plan_details
        )
        db.add(trip_plan)
        db.commit()
        
        return {"message": f"Trip plan '{trip_name}' saved successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving trip plan: {str(e)}")

@app.get("/trips")
async def get_all_trips(user_id: str = "demo_user"):
    """Get all saved trips for a user"""
    db = next(get_db())
    
    try:
        uid = int(user_id) if user_id != "demo_user" else 0
        trips = db.query(TripPlan).filter(TripPlan.user_id == uid).all()
        return {
            "trips": [
                {
                    "id": trip.id,
                    "trip_name": trip.trip_name,
                    "destination": trip.destination,
                    "created_at": trip.created_at.isoformat()
                }
                for trip in trips
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trips: {str(e)}")

@app.get("/trip/{trip_name}")
async def get_trip_details(trip_name: str, user_id: str = "demo_user"):
    """Get details of a specific trip including images"""
    db = next(get_db())
    
    try:
        uid = int(user_id) if user_id != "demo_user" else 0
        
        # Get trip plan
        trip_plan = db.query(TripPlan).filter(
            TripPlan.trip_name == trip_name,
            TripPlan.user_id == uid
        ).first()
        
        # Get trip images
        images = db.query(TripImage).filter(
            TripImage.trip_name == trip_name,
            TripImage.user_id == uid
        ).all()
        
        if not trip_plan and not images:
            raise HTTPException(status_code=404, detail="Trip not found")
        
        image_list = []
        for img in images:
            image_base64 = base64.b64encode(img.image_data).decode('utf-8')
            image_list.append({
                "id": img.id,
                "name": img.image_name,
                "category": img.category,
                "tags": img.tags.split(",") if img.tags else [],
                "data": f"data:image/jpeg;base64,{image_base64}"
            })
        
        return {
            "trip_name": trip_name,
            "destination": trip_plan.destination if trip_plan else "N/A",
            "plan_details": trip_plan.plan_details if trip_plan else "No plan saved",
            "images": image_list,
            "image_count": len(image_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trip details: {str(e)}")

@app.delete("/trip/{trip_name}")
async def delete_trip(trip_name: str):
    """Delete a trip and all associated images"""
    db = next(get_db())
    
    try:
        # Delete trip plan
        db.query(TripPlan).filter(TripPlan.trip_name == trip_name).delete()
        
        # Delete trip images
        db.query(TripImage).filter(TripImage.trip_name == trip_name).delete()
        
        db.commit()
        
        return {"message": f"Trip '{trip_name}' deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting trip: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
