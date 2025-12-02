import os
import tempfile

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.services.csv_reader import BankCSVReader
from app.utils.encoding import encode_base64url

router = APIRouter(prefix="/api/upload-csv", tags=["upload"])


class UploadResponse(BaseModel):
    message: str
    count: int
    id: str


@router.post("", dependencies=[Depends(get_current_user)])
async def upload_csv(file: UploadFile = File(...)) -> UploadResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    records = BankCSVReader(tmp_path).parse()

    filename = os.path.basename(tmp_path)
    file_id = os.path.splitext(filename)[0]  # tmpXXXX
    encoded = encode_base64url(file_id)

    return UploadResponse(
        message="File uploaded successfully",
        count=len(records),
        id=encoded,
    )
