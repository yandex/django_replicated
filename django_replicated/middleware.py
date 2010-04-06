# -*- coding:utf-8 -*-
import utils

class ReplicationMiddleware:
    '''
    Middleware for automatically switching routing state to
    master or slave depending on request method.

    In a properly designed web applications GET and HEAD request should
    not require writing to a database (except by side effects). This
    middleware switches database wrapper to slave mode for such requests.

    One special case is handling redirect responses after POST requests
    doing writes to database. They are most commonly used to show updated
    pages to a user. However in this case slave replicas may not yet be
    updated to match master. Thus first redirect after POST is pointed to
    master connection even if it only GETs data.
    '''
    def process_request(self, request):
        state = request.method in ['GET', 'HEAD'] and 'slave' or 'master'
        state = utils.check_state_override(request, state)
        router = utils._use_state(state)
        if router:
            # Set an attribute on the request to signal process_response that
            # it should indeed call 'revert'
            request._replication_middleware_state = router.state()

    def process_response(self, request, response):
        utils.handle_updated_redirect(request, response)
        if hasattr(request, '_replication_middleware_state'):
            utils._revert()
        return response
