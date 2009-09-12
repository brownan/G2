# -*- coding: utf-8 -*-
"""
All forum logic is kept here - displaying lists of forums, threads 
and posts, adding new threads, and adding replies.
"""

from datetime import datetime
from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseForbidden, HttpResponseNotAllowed
from django.template import RequestContext, Context, loader
from django import forms
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.defaultfilters import striptags, wordwrap
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list

from forum.models import *
from forum.forms import *

FORUM_PAGINATION = getattr(settings, 'FORUM_PAGINATION', 10)
LOGIN_URL = getattr(settings, 'LOGIN_URL', '/accounts/login/')

def forums_list(request):
    
  forums = Forum.objects.for_groups(request.user.groups.all()).select_related().filter(parent__isnull=True).order_by('sort_order')
  categories = []
  for category in Category.objects.select_related().all().order_by('sort_order'):
    categories.append({'name': category.name, 'object':category.forums.all().order_by('sort_order')})
    
  return render_to_response('forum/forum_list.html', {'categories': categories}, context_instance=RequestContext(request))

def forum(request, slug):
    """
    Displays a list of threads within a forum.
    Threads are sorted by their sticky flag, followed by their 
    most recent post.
    """
    try:
        f = Forum.objects.for_groups(request.user.groups.all()).select_related().get(slug=slug)
    except Forum.DoesNotExist:
        raise Http404

    form = CreateThreadForm()
    child_forums = f.child.for_groups(request.user.groups.all())
    return object_list( request,
                        queryset=f.thread_set.select_related().all(),
                        paginate_by=FORUM_PAGINATION,
                        template_object_name='thread',
                        template_name='forum/thread_list.html',
                        extra_context = {
                            'forum': f,
                            'child_forums': child_forums,
                            'form': form,
                        })

def thread(request, thread, editid=None):
    """
    Increments the viewed count on a thread then displays the 
    posts for that thread, in chronological order.
    """
    try:
        t = Thread.objects.select_related().get(pk=thread)
        if not Forum.objects.has_access(t.forum, request.user.groups.all()):
            raise Http404, "insufficient permissions"
    except Thread.DoesNotExist:
        raise Http404, "thread does not exist"
    
    perm = request.user.has_perm("forum.edit_post")
    
    p = t.post_set.extra(select={'can_edit': 'author_id = %s OR %s'}, 
    select_params=[request.user.id, int(perm)]).select_related('author').all().order_by('time')
    s = None
    page = request.REQUEST.get("page", 1)
    if request.user.is_authenticated():
        s = t.subscription_set.select_related().filter(author=request.user)
        #last read post system
        last_post = min((page*FORUM_PAGINATION, p.count()))-1
        try:
          lastread = LastRead.objects.get(user=request.user, thread=t)
          lastread.post = p[last_post]
          lastread.save()
        except LastRead.DoesNotExist:
          LastRead(user=request.user, thread=t, post=p[last_post]).save()
          

    t.views += 1
    t.save()

    if s:
        initial = {'subscribe': True}
    else:
        initial = {'subscribe': False}

    form = ReplyForm(initial=initial)
    
    if editid:
      try:
        post = p.get(pk=editid)
      except Post.DoesNotExist:
        raise Http404
      edit_form = EditForm(instance=post)
      editid = int(editid)
    else:
      edit_form = None
    
    can_lock = can_sticky = True
    
    return object_list( request,
                        queryset=p,
                        paginate_by=FORUM_PAGINATION,
                        template_object_name='post',
                        template_name='forum/thread.html',
                        extra_context = {
                            'forum': t.forum,
                            'thread': t,
                            'subscription': s,
                            'form': form,
                            'editid':editid,
                            'edit_form':edit_form,
                            'page':page,
                            'can_lock':can_lock,
                            'can_sticky':can_sticky,
                            #'body':edit_form.body,
                        })

def mod_action(request, threadid=None, action=None):
  if not (threadid and action):
    return Http404
  try:
    thread = Thread.objects.get(pk=threadid)
    author = thread.post_set.select_related("author").all()[0].author
  except Thread.DoesNotExist:
    raise Http404
  
  if action == "lock":
    if not (request.user.has_perm("forum.lock_thread") or (author != request.user)):
      raise Http404
    thread.closed = True
    thread.save()
    return HttpResponseRedirect(thread.get_absolute_url())
    
  elif action == "unlock":
    if not (request.user.has_perm("forum.lock_thread") or (author != request.user)):
      raise Http404
    thread.closed = False
    thread.save()
    return HttpResponseRedirect(thread.get_absolute_url())
    
  elif action == "sticky":
    if not request.user.has_perm("forum.sticky_thread"):
      raise Http404
    thread.sticky = True
    thread.save()
    return HttpResponseRedirect(thread.get_absolute_url())
    
  elif action == "unsticky":
    if not request.user.has_perm("forum.sticky_thread"):
      raise Http404
    thread.sticky = False
    thread.save()
    return HttpResponseRedirect(thread.get_absolute_url())
    
  else:
    raise Http404
  


def edit_post(request, postid=None):
  if postid is None: 
    raise Http404

  try:
    post = Post.objects.select_related("thread", "author").get(pk=postid)
  except Post.DoesNotExist:
    raise Http404
  
  if (request.user.has_perm("forum.edit_post") or post.author == request.user) and request.method == "POST":
    form = EditForm(request.POST, instance=post)
    if form.is_valid():  
      form.save()
      
  return HttpResponseRedirect(post.get_absolute_url())
  
    

def reply(request, thread):
    """
    If a thread isn't closed, and the user is logged in, post a reply
    to a thread. Note we don't have "nested" replies at this stage.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (LOGIN_URL, request.path))
    t = get_object_or_404(Thread, pk=thread)
    if t.closed:
        return HttpResponseServerError()
    if not Forum.objects.has_access(t.forum, request.user.groups.all()):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            body = form.cleaned_data['body']
            p = Post(
                thread=t, 
                author=request.user,
                body=body,
                time=datetime.now(),
                )
            p.save()

            sub = Subscription.objects.filter(thread=t, author=request.user)
            if form.cleaned_data.get('subscribe',False):
                if not sub:
                    s = Subscription(
                        author=request.user,
                        thread=t
                        )
                    s.save()
            else:
                if sub:
                    sub.delete()

            # Subscriptions are updated now send mail to all the authors subscribed in
            # this thread.
            mail_subject = ''
            try:
                mail_subject = settings.FORUM_MAIL_PREFIX 
            except AttributeError:
                mail_subject = '[Forum]'

            mail_from = ''
            try:
                mail_from = settings.FORUM_MAIL_FROM
            except AttributeError:
                mail_from = settings.DEFAULT_FROM_EMAIL

            mail_tpl = loader.get_template('forum/notify.txt')
            c = Context({
                'body': wordwrap(striptags(body), 72),
                'site' : Site.objects.get_current(),
                'thread': t,
                })

            email = EmailMessage(
                    subject=mail_subject+' '+striptags(t.title),
                    body= mail_tpl.render(c),
                    from_email=mail_from,
                    bcc=[s.author.email for s in t.subscription_set.all()],)
            email.send(fail_silently=True)

            return HttpResponseRedirect(p.get_absolute_url())
    else:
        form = ReplyForm()
    
    return render_to_response('forum/reply.html',
        RequestContext(request, {
            'form': form,
            'forum': t.forum,
            'thread': t,
        }))


def newthread(request, forum):
    """
    Rudimentary post function - this should probably use 
    newforms, although not sure how that goes when we're updating 
    two models.

    Only allows a user to post if they're logged in.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (LOGIN_URL, request.path))

    f = get_object_or_404(Forum, slug=forum)
    
    if not Forum.objects.has_access(f, request.user.groups.all()):
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = CreateThreadForm(request.POST)
        if form.is_valid():
            t = Thread(
                forum=f,
                title=form.cleaned_data['title'],
            )
            t.save()

            p = Post(
                thread=t,
                author=request.user,
                body=form.cleaned_data['body'],
                time=datetime.now(),
            )
            p.save()
    
            if form.cleaned_data.get('subscribe', False):
                s = Subscription(
                    author=request.user,
                    thread=t
                    )
                s.save()
            return HttpResponseRedirect(t.get_absolute_url())
    else:
        form = CreateThreadForm()

    return render_to_response('forum/newthread.html',
        RequestContext(request, {
            'form': form,
            'forum': f,
        }))

def updatesubs(request):
    """
    Allow users to update their subscriptions all in one shot.
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (LOGIN_URL, request.path))

    subs = Subscription.objects.select_related().filter(author=request.user)

    if request.POST:
        # remove the subscriptions that haven't been checked.
        post_keys = [k for k in request.POST.keys()]
        for s in subs:
            if not str(s.thread.id) in post_keys:
                s.delete()
        return HttpResponseRedirect(reverse('forum_subscriptions'))

    return render_to_response('forum/updatesubs.html',
        RequestContext(request, {
            'subs': subs,
        }))
      
