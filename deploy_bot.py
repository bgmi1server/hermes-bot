import os
import shutil
import subprocess

def deploy():
    pat = os.environ.get("GITHUB_PAT")
    if not pat:
        print("Error: GITHUB_PAT environment variable is missing.")
        return False
        
    repo_url = f"https://oauth2:{pat}@github.com/bgmi1server/hermes-bot.git"
    tmp_dir = "tmp_deploy_repo"
    
    print("Preparing secure deployment...")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
        
    print("Cloning main repository...")
    if os.system(f"git clone {repo_url} {tmp_dir}") != 0:
        print("Failed to clone repository.")
        return False
        
    print("Copying modified config.py...")
    shutil.copy("config.py", f"{tmp_dir}/config.py")
    
    print("Committing and pushing...")
    os.chdir(tmp_dir)
    os.system('git config user.name "CogniX Auto-Updater"')
    os.system('git config user.email "bot@hermes"')
    os.system('git add config.py')
    
    # Check if there are actually changes to commit
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if not status.stdout.strip():
        print("No changes detected in config.py. Nothing to deploy.")
        return True
        
    os.system('git commit -m "⚙️ Auto-patch: Model configuration disabled via Telegram"')
    if os.system('git push origin main') != 0:
        print("Failed to push changes to GitHub.")
        return False
        
    os.chdir("..")
    shutil.rmtree(tmp_dir)
    print("Deployment pushed to GitHub successfully! Render will now auto-reboot.")
    return True

if __name__ == "__main__":
    deploy()
