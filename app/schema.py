import graphene
from graphene.types.mutation import Mutation
from graphene_django import DjangoObjectType
from .models import Post,Comment

class PostType(DjangoObjectType):
    class Meta:
        model = Post
        fields = ('id','title','body','comments')

class CommentType(DjangoObjectType):
    class Meta:
        model = Comment
        fields = ('id','body','post')

class Query(graphene.ObjectType):
    posts = graphene.List(PostType)
    comments = graphene.List(CommentType)

    def resolve_posts(self,info,**kwargs):
        return Post.objects.all()

    def resolve_comments(self,info,**kwargs):
        return Comment.objects.all()

class CreatePost(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        body = graphene.String(required=True)

    post = graphene.Field(PostType)

    @classmethod
    def mutate(cls,root,info,title,body):
        post = Post()
        post.title = title
        post.body = body
        post.save()

        return CreatePost(post=post) 

class CreateComment(graphene.Mutation):
    class Arguments:
        post_id = graphene.ID(required=True)
        body = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    @classmethod
    def mutate(cls,root,info,post_id,body):
        comment = Comment()
        comment.post = Post.objects.filter(id=post_id).first()
        comment.body = body
        comment.save()

        return CreateComment(comment=comment)

class Mutation(graphene.ObjectType):
    create_post = CreatePost.Field()
    create_comment = CreateComment.Field()

schema = graphene.Schema(query=Query,mutation=Mutation)