from mitmproxy import http

KEYWORDS = ('inke', 'chat', 'danmu', 'im', 'message', 'live')


def request(flow: http.HTTPFlow):
    url = flow.request.pretty_url
    if any(k in url.lower() for k in KEYWORDS):
        print('REQ %s %s' % (flow.request.method, url), flush=True)


def response(flow: http.HTTPFlow):
    url = flow.request.pretty_url
    if not any(k in url.lower() for k in KEYWORDS):
        return
    print('RESP %s %s status=%s len=%s' % (
        flow.request.method, url, flow.response.status_code, len(flow.response.content)
    ), flush=True)
    try:
        text = flow.response.text[:1500]
        print('BODY %s' % text.replace('\n', ' '), flush=True)
    except Exception:
        print('BODY <binary>', flush=True)
