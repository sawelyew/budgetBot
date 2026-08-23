from io import BytesIO
import aioboto3

from app.config import config


class S3Service:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = config.minio_url
        self.access_key = config.MINIO_ROOT_USER
        self.secret_key = config.MINIO_ROOT_PASSWORD
        self.bucket_name = config.MINIO_BUCKET_NAME

    def _get_client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def init_bucket(self):
        async with self._get_client() as client:
            response = await client.list_buckets()
            buckets = [i["Name"] for i in response.get("Buckets", [])]
            if self.bucket_name not in buckets:
                await client.create_bucket(Bucket=self.bucket_name)

    async def upload_file(self, file_bytes: BytesIO, object_name: str) -> str:
        async with self._get_client() as client:
            await client.upload_fileobj(
                Fileobj=file_bytes,
                Bucket=self.bucket_name,
                Key=object_name,
            )
        return object_name

    async def get_file_bytes(self, object_name: str) -> bytes:
        async with self._get_client() as client:
            response = await client.get_object(
                Bucket=self.bucket_name, Key=object_name
            )
            async with response["Body"] as stream:
                return await stream.read()


s3_service = S3Service()