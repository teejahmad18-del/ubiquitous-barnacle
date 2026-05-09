from django.urls import path
from .views import trigger_bot, get_output, bot_status  # Updated import

urlpatterns = [
    path('run/', trigger_bot, name='run_bot'),
    path('output/', get_output, name='bot_output'),  # Now matches view name
    path('status/', bot_status, name='bot_status'),
]