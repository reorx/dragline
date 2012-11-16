import os


def in_dir_1(pth, dir):
    """
    ('dir0/dir1', 'dir0') True
    ('dir0', 'dir0') True
    ('file.py', '') True
    ('', '') True
    """
    if not dir:
        return True
    if pth == dir:
        return True
    # avoid os.path.relpath('', dir)
    if not pth:
        if not dir:
            return True
        else:
            return False
    rel = os.path.relpath(pth, dir)
    if os.path.join(dir, rel) == pth:
        return True
    else:
        return False


def test_in_dir():
    for i in [
        ('dir0/dir1', 'dir0', True),
        ('dir0/dir1/a.py', 'dir0/dir1', True),
        ('dir0/dir2/a.py', 'dir0', True),
        ('dir0/dir2/a.py', 'dir0/dir1', False),
        ('dir0', 'dir0', True),
        ('dir0/a.py', 'dir0', True),
        ('dir1', 'dir0', False),
        ('file.py', '', True),
        ('dir0/file.py', '', True),
        ('dir0/dir1/file.py', '', True),
        ('', '', True),
        ('', 'dir0', False),
    ]:
        print '%s in %s: %s' % i
        print 'func1:'
        assert in_dir_1(i[0], i[1]) is i[2]
        print 'func2:'
        assert in_dir_2(i[0], i[1]) is i[2]
        print ''


def in_dir_2(pth, dir):
    if not dir:
        return True
    if pth == dir:
        return True
    if not pth.startswith(dir):
        return False
    if os.path.dirname(pth[len(dir):]).startswith('/'):
        return True
    else:
        return False
