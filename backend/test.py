# test_transcription_service.py
# Test your actual transcription service implementation

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

# Set environment variables
os.environ["TOKENIZERS_PARALLELISM"] = "false"

async def test_transcription_service():
    """Test your actual TranscriptionService class"""
    
    try:
        # Import your actual service
        from app.services.transcription_service import TranscriptionService
        from app.config import settings
        
        print("🔍 Testing TranscriptionService...")
        
        # Initialize service
        service = TranscriptionService()
        
        # Test 1: Check if Qdrant client is initialized
        if service.qdrant_client is None:
            print("❌ Qdrant client is None - check your service initialization")
            return False
            
        print("✅ Qdrant client initialized")
        
        # Test 2: Check if embedder is working
        if service.embedder is None:
            print("❌ Embedder is None - check your service initialization")
            return False
            
        print("✅ Embedder initialized")
        
        # Test 3: Try the debug method if it exists
        if hasattr(service, 'debug_qdrant_connection'):
            print("🔍 Running debug_qdrant_connection...")
            debug_result = await service.debug_qdrant_connection("test_user_123")
            print(f"📊 Debug result: {debug_result}")
        
        # Test 4: Try test storage if it exists
        if hasattr(service, 'test_qdrant_storage'):
            print("🔍 Running test_qdrant_storage...")
            storage_result = await service.test_qdrant_storage("test_user_123")
            print(f"📊 Storage test result: {storage_result}")
        
        # Test 5: Test basic Qdrant operations manually
        print("🔍 Testing basic Qdrant operations...")
        
        # Get collections
        collections = service.qdrant_client.get_collections()
        print(f"✅ Collections found: {len(collections.collections)}")
        
        # Test collection creation
        test_collection = "manual_test_collection"
        try:
            from qdrant_client.models import VectorParams, Distance
            
            # Delete if exists
            try:
                service.qdrant_client.delete_collection(test_collection)
                print("🗑️ Deleted existing test collection")
            except:
                pass
            
            # Create collection
            service.qdrant_client.create_collection(
                collection_name=test_collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print("✅ Test collection created")
            
            # Test embedding and storage
            test_text = "This is a test document for manual testing."
            test_vector = service.embedder.encode(test_text).tolist()
            print(f"✅ Embedding created (size: {len(test_vector)})")
            
            # Store a point
            service.qdrant_client.upsert(
                collection_name=test_collection,
                points=[{
                    "id": "test_point_1",
                    "vector": test_vector,
                    "payload": {"text": test_text, "type": "manual_test"}
                }]
            )
            print("✅ Point stored successfully")
            
            # Test search
            search_results = service.qdrant_client.search(
                collection_name=test_collection,
                query_vector=test_vector,
                limit=1
            )
            print(f"✅ Search successful: {len(search_results)} results")
            
            # Clean up
            service.qdrant_client.delete_collection(test_collection)
            print("✅ Test collection cleaned up")
            
        except Exception as e:
            print(f"❌ Manual test failed: {e}")
            return False
        
        print("\n🎉 ALL TESTS PASSED! Your TranscriptionService should work correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the backend directory")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoints():
    """Test your API endpoints"""
    
    try:
        import httpx
        
        print("\n🌐 Testing API Endpoints...")
        
        # Test health endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ Health endpoint working")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
                
        print("📝 To test debug endpoints, you need to:")
        print("1. Start your server: uvicorn app.main:app --reload")
        print("2. Register/login to get a token")
        print("3. Test these endpoints:")
        print("   GET /api/transcriptions/debug/qdrant")
        print("   POST /api/transcriptions/debug/test-storage")
        
    except ImportError:
        print("❌ httpx not installed. Install with: pip install httpx")
    except Exception as e:
        print(f"❌ API test error: {e}")

def check_service_initialization():
    """Check if your service initialization has the fixes"""
    
    print("\n🔧 Checking Service Initialization...")
    
    try:
        # Read the transcription service file
        service_file = Path("app/services/transcription_service.py")
        
        if not service_file.exists():
            print("❌ transcription_service.py not found")
            return
            
        content = service_file.read_text()
        
        # Check for fixes
        checks = [
            ("TOKENIZERS_PARALLELISM", 'os.environ["TOKENIZERS_PARALLELISM"]' in content),
            ("prefer_grpc=False", "prefer_grpc=False" in content),
            ("timeout setting", "timeout=" in content),
            ("error handling", "try:" in content and "except" in content)
        ]
        
        for check_name, found in checks:
            status = "✅" if found else "❌"
            print(f"{status} {check_name}: {found}")
            
        if not all(found for _, found in checks):
            print("\n🔧 Apply these fixes to your TranscriptionService __init__ method:")
            print("""
class TranscriptionService:
    def __init__(self):
        # Fix tokenizers warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        try:
            self.qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=60,
                prefer_grpc=False  # This fixes pydantic errors
            )
            logger.info("✅ Qdrant client initialized")
        except Exception as e:
            logger.error(f"❌ Qdrant initialization failed: {e}")
            self.qdrant_client = None
            
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedder initialized")
        except Exception as e:
            logger.error(f"❌ Embedder initialization failed: {e}")
            self.embedder = None
            """)
            
    except Exception as e:
        print(f"❌ Error checking service file: {e}")

async def main():
    """Run all tests"""
    
    print("🚀 TRANSCRIPTION SERVICE TESTING")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Not in backend directory. Run this from: cd backend")
        return
    
    # Check service file
    check_service_initialization()
    
    # Test the actual service
    success = await test_transcription_service()
    
    # Test API endpoints
    await test_api_endpoints()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Your transcription service is working!")
        print("\n🎯 Next steps:")
        print("1. Start your server: uvicorn app.main:app --reload")
        print("2. Test with a real transcription")
        print("3. Check the debug endpoints via your API")
    else:
        print("❌ ISSUES FOUND: Apply the fixes shown above")

if __name__ == "__main__":
    asyncio.run(main())