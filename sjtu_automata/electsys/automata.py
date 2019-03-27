from time import sleep

import requests
from requests.exceptions import RequestException
from tenacity import retry, retry_if_exception_type, wait_fixed

from sjtu_automata.utils import (re_search, get_timestamp)
from sjtu_automata.utils.exceptions import AutomataError


@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(1))
def _request(session, method, url, params=None, data=None):
    """Request with params.

    Easy to use requests and auto retry.

    Args:
        session: requests session, login session.
        method: string, 'POST' OR 'GET'.
        url: string, post url.
        params=None: dict, get param.
        data=None: dict, post param.

    Returns:
        requests request.

    Raises:
        AutomataError: method param error.
    """
    if method not in ['POST', 'GET'] or not session:
        raise AutomataError

    req = session.request(method, url, params=params, data=data)
    return req.text


def get_studentid(session):
    """Get student id.

    Parse student id.

    Args:
        session: requests session, login session.

    Returns:
        str, student id.
    """
    params = {'jsdm': '', '_t': get_timestamp()}
    req = _request(
        session, 'GET', 'http://i.sjtu.edu.cn/xtgl/index_initMenu.html', params=params)
    return re_search(r'sessionUserKey" value="(.*?)"', req)


def get_params(session, studentid):
    """Get elect params.

    Parse elect params.

    Args:
        session: requests session, login session.
        studentid: str, student id.

    Returns:
        dict:
            xkkz_id: list, [0] is '主修课程', [1] is '通识课', [2] is '通选课'
            njdm_id: str, njdm_id
            zyh_id: str, zyh_id
    """
    params = {'gnmkdm': 'N253512', 'layout': 'default', 'su': studentid}
    req = _request(
        session, 'GET', 'http://i.sjtu.edu.cn/xsxk/zzxkyzb_cxZzxkYzbIndex.html', params=params)
    xkkz_id = []
    xkkz_id.append(re_search(
        r'\'01\',\'(.*)\'\)" role="tab" data-toggle="tab">', req))
    xkkz_id.append(re_search(
        r'\'10\',\'(.*)\'\)" role="tab" data-toggle="tab">', req))
    xkkz_id.append(re_search(
        r'\'11\',\'(.*)\'\)" role="tab" data-toggle="tab">', req))
    njdm_id = re_search(r'id="njdm_id" value="(.*?)"/>', req)
    zyh_id = re_search(r'id="zyh_id" value="(.*?)"/>', req)
    return {'xkkz_id': xkkz_id, 'njdm_id': njdm_id, 'zyh_id': zyh_id}


def elect_class(session, studentid, params, classtype, classid):
    """Elect class.

    Directly elect class.
    This operation is safe that you dont need to check if you have elected before and so on.

    Args:
        session: requests session, login session.
        studentid: str, student id.
        params: dict, get_params returned
        classtype: int, 0 is '主修课程', 1 is '通识课', 2 is '通选课'
        classid: str, class id

    Returns:
        int, -1 for param error, 0 for success, 1 for time conflict, 2 for full, 3 for param error, 4 for other.
    """
    if not (0 <= classtype <= 2):
        return -1
    post_params = {'gnmkdm': 'N253512', 'su': studentid}
    data = {'jxb_ids': classid, 'xkkz_id': params['xkkz_id'][classtype],
            'njdm_id': params['njdm_id'], 'zyh_id': params['zyh_id']}

    req = _request(
        session, 'POST', 'http://i.sjtu.edu.cn/xsxk/zzxkyzb_xkBcZyZzxkYzb.html', params=post_params, data=data)

    if '{"flag":"1"}' in req:
        return 0
    if '所选教学班的上课时间与其他教学班有冲突' in req:
        return 1
    if '"flag":"-1"' in req:
        return 2
    if '{}' in req:
        return 3
    return 4
