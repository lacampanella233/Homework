def run(repo, args):
    config = repo.config()
    print(f'Repository: {repo.root}\nCurrent branch: {repo.branch()}')
    print('Origin: ' + repo.git('remote', 'get-url', 'origin'))
    print('Courses:')
    for path in sorted(repo.root.iterdir()):
        if path.is_dir() and not path.name.startswith('.'):
            settings = config['courses'].get(path.name)
            defaults = (f"semester={settings['semester']}; language={settings['defaultLanguage']}"
                        if settings else 'defaults not configured')
            print(f'  {path.name} (next: {repo.next_number(path)}; {defaults})')
    print('Local branches:\n' + repo.git('branch', '--format=%(refname:short)'))
    print('Git status:\n' + repo.git('status', '--short', '--branch'))
