from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=150)
    body = models.TextField()
    
    def __str__(self) -> str:
        return self.title

class Comment(models.Model):
    body = models.TextField()
    post = models.ForeignKey(Post,related_name="comments",on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.post.title