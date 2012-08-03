#!/usr/bin/env python
"""Run acid test against latest repositories on Github."""

import os
import re
import subprocess
import sys

import acid


TMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                       'github_tmp')


def latest_repositories():
    """Return names of latest released repositories on Github."""
    import requests

    for result in requests.get('https://github.com/timeline.json').json:
        try:
            repository = result['repository']
            size = repository['size']
            if 0 < size < 1000 and repository['language'] == 'Python':
                yield repository['url']
        except KeyError:
            continue


def download_repository(name, output_directory):
    """Download repository to output_directory.

    Raise CalledProcessError on failure.

    """
    subprocess.check_call(['git', 'clone', name],
                          cwd=output_directory)


def interesting(repository_path):
    """Return True if interesting."""
    print(repository_path)
    process = subprocess.Popen(['git', 'log'],
                               cwd=repository_path,
                               stdout=subprocess.PIPE)
    return len(re.findall(
        'pep8',
        process.communicate()[0].decode('utf-8'))) > 2


def main():
    """Run main."""
    try:
        os.mkdir(TMP_DIR)
    except OSError:
        pass

    opts, args = acid.process_args()
    if args:
        # Copy
        names = list(args)
    else:
        names = None

    import time
    start_time = time.time()

    checked_repositories = []
    skipped_repositories = []
    interesting_repositories = []
    try:
        while True:
            if opts.timeout > 0 and time.time() - start_time > opts.timeout:
                break

            if args:
                if not names:
                    break
            else:
                while not names:
                    # Continually populate if user did not specify a repository
                    # explicitly.
                    names = [p for p in latest_repositories()
                             if p not in checked_repositories and
                             p not in skipped_repositories]

                    if not names:
                        import time
                        time.sleep(1)

            repository_name = names.pop(0)
            print(repository_name)

            user_tmp_dir = os.path.join(
                TMP_DIR,
                os.path.basename(os.path.split(repository_name)[0]))
            try:
                os.mkdir(user_tmp_dir)
            except OSError:
                pass

            repository_tmp_dir = os.path.join(
                user_tmp_dir,
                os.path.basename(repository_name))
            try:
                os.mkdir(repository_tmp_dir)
            except OSError:
                print('Skipping already checked repository')
                skipped_repositories.append(repository_name)
                continue

            try:
                download_repository(repository_name,
                                    output_directory=repository_tmp_dir)
            except subprocess.CalledProcessError:
                print('ERROR: git clone failed')
                continue

            if acid.check(opts, [repository_tmp_dir]):
                checked_repositories.append(repository_name)

                if interesting(
                    os.path.join(repository_tmp_dir,
                                 os.path.basename(repository_name))):
                    interesting_repositories.append(repository_name)
            else:
                return 1
    except KeyboardInterrupt:
        pass

    if checked_repositories:
        print('\nTested repositories:')
        for name in checked_repositories:
            print('    ' + name +
                  (' *' if name in interesting_repositories else ''))

if __name__ == '__main__':
    sys.exit(main())