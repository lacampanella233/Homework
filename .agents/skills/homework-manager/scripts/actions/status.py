def run(repo, args):
    config = repo.config()
    print(f'Repository: {repo.root}\nCurrent branch: {repo.branch()}')
    print('Origin: ' + repo.git('remote', 'get-url', 'origin'))
    print(f"Defaults: semester={config['semester']}; language={config['defaultLanguage']}")
    print('Courses:')
    for path in sorted(repo.root.iterdir()):
        if path.is_dir() and not path.name.startswith('.'):
            print(f'  {path.name} (next: {repo.next_number(path)})')
    print('Local branches:\n' + repo.git('branch', '--format=%(refname:short)'))
    print('Git status:\n' + repo.git('status', '--short', '--branch'))
