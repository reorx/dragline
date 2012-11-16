
import os
import fnmatch


def conditioinal_walk(root, ignores, *args, **kwgs):
    print 'execute once'

    dir_ignores = []
    file_ignores = []

    for i in ignores:
        if i.endswith('/'):
            dir_ignores.append(i[:-1])
        else:
            file_ignores.append(i)

    print 'dir_ignores', dir_ignores
    print 'file_ignores', file_ignores
    print ''

    def file_filter(filepath):
        for i in file_ignores:
            if fnmatch.fnmatch(filepath, i):
                return False
        return True

    for dirpath, dirnames, filenames in os.walk(root, *args, **kwgs):
        rel_prefix = os.path.relpath(dirpath, root)
        dirnames[:] = [i for i in dirnames
                       if os.path.join(rel_prefix, i) not in dir_ignores]
        filenames[:] = [i for i in filenames
                        if file_filter(os.path.join(rel_prefix, i))]
        yield dirpath, dirnames, filenames

    print 'over'


if __name__ == '__main__':
    import time
    t0 = time.time()
    for dirpath, dirnames, filenames in conditioinal_walk('dir0', ['dir1/dir3/', 'dir1/*.py']):
        print 'dirpath: %s/' % dirpath
        print '----dirnames:'
        for i in dirnames:
            print i
        print '----filenames:'
        for i in filenames:
            print i
        print '====end\n'
    t1 = time.time()

    print 'time: ', t1 - t0
