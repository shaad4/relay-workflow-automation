
import os

from supabase import Client, create_client


class SupabaseStorage:

    def __init__(self):
        self.bucket = os.environ["SUPABASE_STORAGE_BUCKET"]

        self.client: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SECRET_KEY"],
        )

    def upload(
        self,
        file_content: bytes,
        storage_path: str,
        content_type: str,
    ) -> str:
        self.client.storage.from_(self.bucket).upload(
            path=storage_path,
            file=file_content,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )

        return storage_path

    def download(self, storage_path: str) -> bytes:
        return self.client.storage.from_(
            self.bucket
        ).download(storage_path)

    def delete(self, storage_path: str) -> None:
        self.client.storage.from_(
            self.bucket
        ).remove([storage_path])

    def exists(self, storage_path: str) -> bool:
        folder, filename = storage_path.rsplit("/", 1)

        objects = self.client.storage.from_(
            self.bucket
        ).list(
            path=folder,
            options={"search": filename},
        )

        return any(
            obj["name"] == filename
            for obj in objects
        )
