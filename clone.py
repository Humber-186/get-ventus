import os
import subprocess
import shutil

LOCAL_PREBUILD_PATH = "/home/common/ventus-toolchain-prebuild"

def rodinia_after_clone(repo_path):
    """ Get data tar.gz file for rodinia after cloning the repository. """
    data_path = os.path.join(repo_path, "data")
    if(os.path.exists(f"{LOCAL_PREBUILD_PATH}/gpu-rodinia-data")):
        shutil.copytree(
            f"{LOCAL_PREBUILD_PATH}/gpu-rodinia-data",
            data_path,
            dirs_exist_ok=True
        )
    else:
        # Download zip and extract from https://www.dropbox.com/s/cc6cozpboht3mtu/rodinia-3.1-data.tar.gz
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        tgz_url = "https://www.dropbox.com/s/cc6cozpboht3mtu/rodinia-3.1-data.tar.gz"
        tgz_path = os.path.join(data_path, "rodinia-3.1-data.tar.gz")
        try:
            subprocess.run(["curl", "-L", tgz_url, "-o", tgz_path], check=True)
            subprocess.run(["tar", "-xf", tgz_path, "-C", data_path], check=True)
            os.remove(tgz_path)
            print(f"Downloaded and extracted gpu-rodinia dataset to {repo_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to download or extract prebuilt binary: {e}")

# 定义常用的仓库信息
repositories = {
    "llvm": {
        "github": "THU-DSP-LAB/llvm-project",
        "prebuild-local": f"{LOCAL_PREBUILD_PATH}/llvm-ventus-prebuild",
    },
    "pocl": {
        "github": "THU-DSP-LAB/pocl",
        "branch": "dev-devices",
    },
    "ocl-icd": {
        "github": "OCL-dev/ocl-icd",
    },
    "spike": {
        "github": "THU-DSP-LAB/ventus-gpgpu-isa-simulator",
    },
    "driver": {
        "github": "THU-DSP-LAB/ventus-driver",
        "branch": "dev-devices",
    },
    "rodinia": {
        "github": "THU-DSP-LAB/gpu-rodinia",
        "after-clone": rodinia_after_clone,
    },
    "gpgpu": {
        "github": "THU-DSP-LAB/ventus-gpgpu",
        "branch": "dev-2024",
    },
    "simulator": {
        "github": "THU-DSP-LAB/ventus-gpgpu-cpp-simulator",
        "branch": "develop",
    },
}

build_seq = ["llvm", "ocl-icd", "libclc", "spike", "driver", "pocl", "rodinia", "test-pocl"]

def create_directory(directory):
    """创建目标目录，如果已存在则提示"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")
    else:
        print(f"Directory already exists: {directory}")

def clone_repo(repo_name, target_folder):
    """克隆或更新仓库，支持重试和branch切换"""
    repo_info = repositories.get(repo_name)
    if not repo_info:
        print(f"Unknown repository: {repo_name}")
        return

    clone_method = repo_info["clone_method"]
    repo_dir = os.path.join(target_folder, repo_name)
    repositories[repo_name]["path"] = repo_dir  # 更新仓库路径
    branch = repo_info.get("branch")

    # 一般方式：clone github仓库
    if clone_method in ["https", "ssh"]:
        # 构造仓库URL
        if clone_method == "https":
            repo_url = f"https://github.com/{repo_info['github']}.git"
        else:
            repo_url = f"git@github.com:{repo_info['github']}.git"

        # 检查仓库是否已存在
        if os.path.exists(repo_dir):
            print(f"Repository {repo_name} already exists at {repo_dir}")
            print("NOTE: You may need to git pull to update it.")
            if branch:
                print(f"Switching to branch {branch}...")
                try:
                    subprocess.run(["git", "-C", repo_dir, "checkout", branch], check=True)
                    print(f"Switched to branch {branch}")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to switch branch: {e}")
            return

        # 执行clone，支持重试
        while True:
            try:
                if branch:
                    command = ["git", "clone", "--recursive", "-b", branch, repo_url, repo_dir]
                else:
                    command = ["git", "clone", "--recursive", repo_url, repo_dir]
                print(f"Cloning {repo_name} from {repo_url}...")
                subprocess.run(command, check=True)
                print(f"Successfully cloned {repo_name}")
                break
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {repo_name}: {e}")
                retry = input("Do you want to retry? (y/n): ").strip().lower()
                if retry != "y":
                    print(f"Skipping {repo_name}")
                    break
    
    # 预构建二进制：从本地共享目录复制或下载
    elif clone_method == "prebuild-binary":
        prebuild_path = repo_info["prebuild-local"]
        if os.path.exists(prebuild_path):
            try:
                shutil.copytree(prebuild_path, repo_dir, dirs_exist_ok=True)
                print(f"Copied prebuilt binary from {prebuild_path} to {repo_dir}")
            except Exception as e:
                print(f"Failed to copy prebuilt binary: {e}")
        else:
            # TODO: check if this is correct
            tgz_url = "http://dspdev.ime.tsinghua.edu.cn/images/ventus-release-v2.2.0-ubuntu22.04.tar.gz"
            tgz_path = os.path.join(target_folder, f"{repo_name}.tar.gz")
            try:
                print(f"Downloading prebuilt binary for {repo_name}...")
                subprocess.run(["curl", "-L", tgz_url, "-o", tgz_path], check=True)
                subprocess.run(["tar", "-xf", tgz_path, "-C", repo_dir], check=True)
                os.remove(tgz_path)
                print(f"Downloaded and extracted prebuilt binary to {repo_dir}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to download or extract prebuilt binary: {e}")

    else:
        print(f"Invalid clone method: {clone_method}")
    
    if "after-clone" in repo_info:
        after_clone_func = repo_info["after-clone"]
        if callable(after_clone_func):
            after_clone_func(repo_dir)

def main():
    """主函数，处理用户输入并执行clone"""
    # 获取目标文件夹
    target_folder = input("Enter the directory to clone repositories into (default: ./ventus): ") or "./ventus"
    create_directory(target_folder)

    # 为每个仓库选择clone方式
    for repo_name in repositories.keys():
        default_method = "https" if ("prebuild-local" not in repositories[repo_name]) else "prebuild-binary"
        if(default_method == "prebuild-binary"):
            prebuild_path = repositories[repo_name]["prebuild-local"]
            if (not os.path.exists(prebuild_path)) or (not os.access(prebuild_path, os.R_OK)):
                default_method = "https"
        useable_clone_methods = ["https", "ssh"]
        if(default_method == "prebuild-binary"):
            useable_clone_methods.append("prebuild-binary")
        clone_method = input(f"How would you like to clone {repo_name}? ({'/'.join(useable_clone_methods)})(default {default_method}): ").strip().lower() or default_method
        repositories[repo_name]["clone_method"] = clone_method
    
    print("You may need to set proxy for git/curl first.")
    print("Is that OK? Press Enter to continue: ")
    input()

    # clone或更新各仓库
    for repo_name in repositories.keys():
        clone_repo(repo_name, target_folder)
    
    shutil.copyfile("build-ventus.sh", os.path.join(target_folder, "build-ventus.sh"))
    shutil.copyfile("env.sh", os.path.join(target_folder, "env.sh"))
    print("All repositories have been cloned or updated successfully.")
    print("You can now run the build script in the target directory:")
    print(f"    cd {target_folder} && ./build-ventus.sh")
    print("Make sure all dependencies are installed.")

if __name__ == "__main__":
    main()