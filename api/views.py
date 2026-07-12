from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def api_status(request):
    """Simple endpoint to verify Django REST Framework connectivity"""
    return Response({
        "status": "online",
        "message": "Django REST Framework backend is successfully configured and connected!"
    })
