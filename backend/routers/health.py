from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "ProcureAI API ready", "version": "4.0.0"}
