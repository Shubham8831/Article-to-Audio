from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from typing import Optional

app = FastAPI(
    title="Indian Railway PNR Status API",
    description="Check PNR status of Indian Railway tickets",
    version="1.0.0"
)

class PNRStatusResponse(BaseModel):
    pnr: str
    train_number: Optional[str] = None
    train_name: Optional[str] = None
    boarding_point: Optional[str] = None
    destination: Optional[str] = None
    date_of_journey: Optional[str] = None
    passenger_status: Optional[list] = None
    chart_status: Optional[str] = None
    message: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Indian Railway PNR Status API",
        "endpoints": {
            "/pnr/{pnr_number}": "Get PNR status",
            "/docs": "API documentation"
        }
    }

@app.get("/pnr/{pnr_number}", response_model=PNRStatusResponse)
async def get_pnr_status(pnr_number: str):
    """
    Get PNR status for Indian Railway ticket
    
    Parameters:
    - pnr_number: 10-digit PNR number
    
    Example: /pnr/1234567890
    """
    
    # Validate PNR format
    if not pnr_number.isdigit() or len(pnr_number) != 10:
        raise HTTPException(
            status_code=400, 
            detail="Invalid PNR number. Must be 10 digits."
        )
    
    # API key
    api_key = "674f63aeabmshaba5c1e4e847a96p144272jsnc2fcbd8db22c"
    
    try:
        # API endpoint
        url = f"https://real-time-pnr-status-api-for-indian-railways.p.rapidapi.com/name/{pnr_number}"
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "real-time-pnr-status-api-for-indian-railways.p.rapidapi.com"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Return parsed response
                return {
                    "pnr": pnr_number,
                    "train_number": data.get("trainNumber") or data.get("trainNo"),
                    "train_name": data.get("trainName"),
                    "boarding_point": data.get("from") or data.get("boardingPoint"),
                    "destination": data.get("to") or data.get("destinationStation"),
                    "date_of_journey": data.get("doj") or data.get("dateOfJourney"),
                    "passenger_status": data.get("passengers") or data.get("passengerList", []),
                    "chart_status": data.get("chartPrepared") or data.get("chartStatus"),
                    "message": data.get("message") or "PNR status fetched successfully"
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"API request failed: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request timeout. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching PNR status: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    print("""
    🚂 Indian Railway PNR Status API
    
    Ready to use! API key is already configured.
    
    The API is available at http://localhost:8000
    API Documentation: http://localhost:8000/docs
    
    Example usage: http://localhost:8000/pnr/2608290686
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)