import graphene
from graphene.types.mutation import Mutation
from graphene_django import DjangoObjectType
from .models import Post,Comment
from graphene_django.forms.mutation import DjangoModelFormMutation
from graphene_django.filter import DjangoFilterConnectionField
from .forms import PostForm,CommentForm
import QL.utils as utils
from graphene.relay.node import from_global_id

class PostType(DjangoObjectType):
    class Meta:
        model = Post
        filter_fields = ('id','title','body','comments')
        interfaces = (graphene.relay.Node,)

class CommentType(DjangoObjectType):
    class Meta:
        model = Comment
        filter_fields = ('id','body','post')
        interfaces = (graphene.relay.Node,)

class Query(graphene.ObjectType):
    # posts = graphene.List(PostType)
    # comments = graphene.List(CommentType)

    post = graphene.relay.Node.Field(PostType)
    posts = DjangoFilterConnectionField(PostType)

    comment = graphene.relay.Node.Field(CommentType)
    comments = DjangoFilterConnectionField(CommentType)

    # def resolve_posts(self,info,**kwargs):
    #     return Post.objects.all()

    # def resolve_comments(self,info,**kwargs):
    #     return Comment.objects.all()

class PostMutation(DjangoModelFormMutation):
    class Meta:
        form_class = PostForm

class CommentMutation(utils.GraphqlModelFormMutation):
    class Meta:
        form_class = CommentForm
        exclude_fields = ["id"]

    def clean(self, **input):
        input["post"] = from_global_id(input.get("post"))[1]
        # item = input.get("post")
        # utils.from_global_id_multiple(["id"], item)
        
        return input

class Mutation(graphene.ObjectType):
    create_post = PostMutation.Field()
    create_comment = CommentMutation.Field()

# class CreatePost(graphene.Mutation):
#     class Arguments:
#         title = graphene.String(required=True)
#         body = graphene.String(required=True)

#     post = graphene.Field(PostType)

#     @classmethod
#     def mutate(cls,root,info,title,body):
#         post = Post()
#         post.title = title
#         post.body = body
#         post.save()

#         return CreatePost(post=post) 

# class CreateComment(graphene.Mutation):
#     class Arguments:
#         post_id = graphene.ID(required=True)
#         body = graphene.String(required=True)

#     comment = graphene.Field(CommentType)

#     @classmethod
#     def mutate(cls,root,info,post_id,body):
#         comment = Comment()
#         comment.post = Post.objects.filter(id=post_id).first()
#         comment.body = body
#         comment.save()

#         return CreateComment(comment=comment)

# class Mutation(graphene.ObjectType):
#     create_post = CreatePost.Field()
#     create_comment = CreateComment.Field()

schema = graphene.Schema(query=Query,mutation=Mutation)