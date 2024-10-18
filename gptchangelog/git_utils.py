import git


def get_commit_messages_since(latest_commit, repo_path=".", min_length=10):
    repo = git.Repo(repo_path)
    commit_messages = set()
    for commit in repo.iter_commits(f"{latest_commit}..HEAD", no_merges=True):
        message = commit.message.strip()
        if len(message) >= min_length:
            commit_messages.add(message)
    return latest_commit, "\n".join(commit_messages)
