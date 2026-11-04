from rest_framework import serializers

from .models import Comment

class CommentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Comment
        fields = ["id", "author", "case", "content", "created_at"]
        read_only_fields = ["id", "author", "case", "created_at"]

    def validate_content(self, text):
        text = text.strip()
        
        if len(text) > 200:
            raise serializers.ValidationError("Comment must not exceed 200 characters.")
        return text
    

