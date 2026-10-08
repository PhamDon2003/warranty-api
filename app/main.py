import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import auth, customers, dealers, products, serials, warranty

app = FastAPI(
    title="Warranty API",
    description="API quản lý vòng đời serial và bảo hành thiết bị",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dealers.router)
app.include_router(customers.router)
app.include_router(serials.router)
app.include_router(warranty.router)

# Mount static folder and serve Web UI at root
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Welcome to Warranty API", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
