import shutil
import re
import os
import json
from subprocess import run, call
import pathlib

CHECKPOINT_SAVE_DIRECTORY="/plotting_save"
KNOWN_TEMP_DIRS = ["/mnt/plotting_dir"]
for d in KNOWN_TEMP_DIRS:
    pathlib.Path(d).mkdir(parents=True, exist_ok=True)
pathlib.Path(CHECKPOINT_SAVE_DIRECTORY=).mkdir(parents=True, exist_ok=True)

def get_filesize_gb(filepath):
    return os.stat(filepath).st_size/(1024*1024*1024)

def checkpoint_proc(job):
    save_dir = f"{CHECKPOINT_SAVE_DIRECTORY}/{job['plot_id']}"
    os.mkdir(save_dir)
    result = run(["sudo", "criu", "dump", "-D", save_dir, "-t", job["pid"], "--shell-job"], capture_output=True, text=True)
    with open(f"{save_dir}/job_details.json", "w+") as f_out:
        json.dump(job, f_out)

def restore_checkpoint_proc(save_dir):
    result = run(["sudo", "criu", "restore", "-d", "-D", f"{CHECKPOINT_SAVE_DIRECTORY}/{save_dir}", "--shell-job"], capture_output=True, text=True)

def plotman_get_status():
    result = run(["plotman", "status"], capture_output=True, text=True)
    if result.stdout:
        jobs = []
        status = result.stdout
        header = False
        for line in status.split("\n")[:-1]:
            if not header:
                header = re.sub("\s+"," ", line).replace('tmp', 'tmp_dir', 1).replace("plot id", "plot_id").split()
            else:
                job = {}
                details = re.sub("\s+"," ", line).split()
                keyvals = zip(header, details)
                for h, d in keyvals:
                    job.setdefault(h, d)
                jobs.append(job)
        return jobs, status
    if result.stderr:
        print(result.stderr)
        return False

def plotman_suspend_all():
    result = run(["plotman", "suspend", "all"], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
        return True
    if result.stderr:
        print(result.stderr)
        return False

def plotman_resume_all():
    result = run(["plotman", "resume", "all"], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
        return True
    if result.stderr:
        print(result.stderr)
        return False

def delete_orphaned_tmp_files(jobs):
    tmp_files_to_move = []
    all_tmp_dirs = []
    all_plot_ids = []
    if jobs:
        for job in jobs:
            plot_id = job["plot_id"]
            tmp_dir = job["tmp_dir"]
            if plot_id not in all_plot_ids:
                all_plot_ids.append(plot_id)
            if tmp_dir not in  all_tmp_dirs:
                all_tmp_dirs.append(tmp_dir)
    else:
        all_tmp_dirs = KNOWN_TEMP_DIRS
    for tmp_dir in all_tmp_dirs:
        for tmp_filename in os.listdir(tmp_dir):
            tmp_filepath = f"{tmp_dir}/{tmp_filename}"
            delete_file = True
            for plot_id in all_plot_ids:
                if plot_id in tmp_filename:
                    delete_file = False
            if delete_file:
                tmp_size = get_filesize_gb(tmp_filepath)
                if tmp_size > 100:
                    del_large = None
                    while del_large != "y" and del_large != "n":
                        del_large = input(f"Found {tmp_filename} is possibly complete (~{tmp_size}GB), Delete? (y/n)")
                        if del_large == "n":
                            tmpfiles_to_move.append(tmp_filepath)
                            continue
                        os.remove(tmp_filepath)
                os.remove(tmp_filepath)

def process_existing_checkpoints(save_dirs):
    unsuspend_action = None
    while unsuspend_action != "y" and unsuspend_action != "n":
        unsuspend_action = input("Found Saved Dirs, Unsuspend all plotter instances? (y/n)")
    if unsuspend_action == "y":
        for d in save_dirs:
            restore_checkpoint_proc(d)
            shutil.rmtree(f"{CHECKPOINT_SAVE_DIRECTORY}/{d}")
        plotman_resume_all()
        return
    elif unsuspend_action == "n":
        tmpfiles_to_move = []
        existing_action = None
        while (existing_action != "y") and (existing_action != "n"):
            existing_action = input("Delete old plotter instance checkpoints? (y/n)")
        if existing_action == "y":
            del_tmpfiles = None
            while (del_tmpfiles != "y") and (del_tmpfiles == "n"):
                del_tmpfiles = input("Delete existing tmp files to free storage space? (y/n)")
            for d in save_dirs:
                if del_tmpfiles == "y":
                    with open(f"{CHECKPOINT_SAVE_DIRECTORY}/{d}/job_details.json","r") as f_in:
                        job = json.load(f_in)
                        for tmp_filename in os.listdir(job["tmp_dir"]):
                            if job["plot_id"] in tmp_filename:
                                tmp_filepath = f"{job['tmpdir']}/{tmp_filename}"
                            tmp_size = get_filesize_gb(tmp_filepath)
                            if tmp_size > 100:
                                del_large = None
                                while not del_large == "y" or del_large == "n":
                                    del_large = input(f"Found {tmp_filename} is possibly complete (~{tmp_size}GB), Delete? (y/n)")
                                if del_large == "n":
                                    tmpfiles_to_move.append(tmp_filepath)
                                    continue
                            os.remove(tmp_filepath)
                shutil.rmtree(d)
    return tmpfiles_to_move

def main():
    assert shutil.which("criu") is not None, "Please install criu binary"
    save_dirs = [ pathname for pathname in os.listdir(CHECKPOINT_SAVE_DIRECTORY) if os.path.isdir(os.path.join(CHECKPOINT_SAVE_DIRECTORY, pathname)) ]
    if save_dirs:
        tmpfiles_to_move = process_existing_checkpoints(save_dirs)
    jobs, status = plotman_get_status()
    print(status)

    suspend_action = None
    while suspend_action != "y" and suspend_action != "n":
        suspend_action = input("Suspend all plotter instances? (y/n)")
    if suspend_action == "y":
        plotman_suspend_all()
        for job in jobs:
            checkpoint_proc(job)

    delete_orphans = None
    while delete_orphans != "y" and delete_orphans != "n":
        delete_orphans = input("Scan for and delete ophaned plotter tmp files? (y/n)")
    if delete_orphans == "y":
        delete_orphaned_tmp_files(jobs)




if __name__ == "__main__":
    main()

