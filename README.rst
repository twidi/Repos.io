OrganizeMyRepositories
======================

The idea
--------

The idea of this project came to me when i searched in my GitHub_ watched projects to find something...

The problem is that Github just give us a list. No description, no way to organize it. Useless.

Then i wanted to create a site for that.

But why only Github ? Why only watched projects ?

So the final goal for this project is to help you organize all projects you own, you follow, you watch, you like on any provider.

But for now, we just start with the watched projects on Github... (from this point, this document will only talk, for now, about this first goal)

Why it can helps me ?
---------------------

By connecting with yor Github account to this site, you'll see a list of all your watched projects. As on Github.

But you will also see the description of each project. And you will be able to tag each project ('django', 'utils', 'book'...).

And we will try to help you organize these projects using tags other users put on them.

I love this idea, can i help you ?
----------------------------------

Yes of course, the source code of this project is on our `GitHub repository`_, you can fork it and send us pull requests, add/resolve issues...

The site is coded using django (1.3), django-social-auth (for authentication) and python-github2 (for access to the github api)

Is that all ?
-------------

For now, yes. We just started this project...

Some notes, for later
---------------------
Providers :
 - github (api: ok (python-github2), auth: oauth2)
 - bitbucket (api: ok, auth: oauth?)
 - pypi (api: ok, auth: not needed)
 - google code (?)

Some possible functionnalities :
 - tree view of forks
 - rss feeds (with filters !)




.. _GitHub: http://www.github.com
.. _GitHub repository: https://github.com/twidi/OrganizeMyRepositories
