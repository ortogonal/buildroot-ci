#!/usr/bin/python
import argparse
import git
import os
import shutil
import sys
import subprocess
from git import Repo
from git import RemoteProgress
from git import Head
import xml.etree.ElementTree

class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "NO MESSAGE")

def mkdir_recursive(path):
    sub_path = os.path.dirname(path)
    if not os.path.exists(sub_path):
        mkdir_recursive(sub_path)
    if not os.path.exists(path):
        os.mkdir(path)

def isRemoteAvailable(remoteToFind, repo):
    remotes = repo.remotes
    for remote in remotes:
        # print remote.name + ":" + remoteToFind;
        if (remote.name == remoteToFind):
            return True
    return False

def isRefAvilable(refToFind, onRemote, repo):
    refs = repo.remote(onRemote).refs
    for ref in refs:
        # print ref.name;
        refPath = onRemote + "/" + refToFind
        if ref.name == refPath:
            return True
    return False

def clearOldBuild(buildDir):
    # TODO: Check if the remote filder os empty after the build folder is deleted
    #       Then delete the remote folder as well.
    if os.path.isdir(buildDir):
        shutil.rmtree(buildDir)
    return True

def createBuildFolder(buildDir):
    if os.path.isdir(buildDir):
        return True

    mkdir_recursive(buildDir)
    return True

#def checkoutBuild(repo, remote, branch):
#    return True

def configureBuild(path, buildPath, defconfig):
    cmd = ["make",  "O=" + buildPath,  "-C", path, defconfig]
    p = subprocess.Popen(cmd, cwd=buildPath)
    p.communicate()
    return True

def compileBuild(path):
    cmd = ["make"]
    p = subprocess.Popen(cmd, cwd=path)
    p.communicate()
    return True

def isRemote(repo, remoteName):
    for remote in repo.remotes:
        if remote.name == remoteName:
            return True
    return False

# TODO: This should be an argument
repoPath = os.path.abspath("repo")
buildPath = os.path.abspath("builds")


# For each branch
#remotes = repo.remotes
#for remote in remotes:
#    print remote.name
#    refs = repo.remote(remote.name).refs
#    refs = repo.remotes[remote.name];
#    for ref in refs:
#        print ref.name;

e = xml.etree.ElementTree.parse('test.xml').getroot()

# Initialize (if needed) repo


# Update repo (all remotes)

# TODO: Make directory recursivly
if os.path.isdir(repoPath) == False:
    mkdir_recursive(repoPath)
    Repo.init(repoPath)

repo = Repo(repoPath);
remotes = repo.remotes
for remotes in e.findall('remotes'):
    for remote in remotes.findall('remote'):
        name = remote.attrib['name']
        remoteUrl = remote.attrib['url']
        if isRemote(repo, name) == False:
            print "Add " + name
            newRemote = repo.create_remote(name, url=remoteUrl)
            if not newRemote.exists():
                print "Remote " + name + " does not exists, exiting"
                exit(1)


errors = False
for builds in e.findall('builds'):
    for b in builds.findall('build'):
        remote = b.attrib['remote'];
        branch = b.attrib['branch'];

        # Check if we have this remote
        if isRemoteAvailable(remote, repo) & isRefAvilable(branch, remote, repo):
            print "Build " + remote + " at " + branch
            print "Using:"
            for configs in b.findall('configs'):
                for c in configs.findall('config'):
                    config = c.attrib['name'];
                    print "    config: " + config;

                    # If the branch exists, rename it and the checkout the new one (if forced)
                    # then remove the renamed branch
                    if branch + "_nn" in repo.heads:
                        repo.heads[branch].rename(branch + "_nn", force=True)

                    # Fetch
                    fetchRemote = repo.remotes[name];
                    for fetch_info in fetchRemote.fetch(progress=MyProgressPrinter()):
                        print("Updated %s to %s" % (fetch_info.ref, fetch_info.commit))

                    # Checkout correct branch
                    repo.create_head(branch, repo.remotes[remote].refs[branch])  # create local branch "master" from remote "master"
                    repo.heads[branch].set_tracking_branch(repo.remotes[remote].refs[branch])  # set local "master" to track remote "master
                    repo.heads[branch].checkout()
                    repo.remotes[remote].pull()

                    # Delete the renamed branch
                    if branch + "_nn" in repo.heads:
                        Head.delete(repo, branch + "_nn", fource=True)

                    # Run build
                    bp = buildPath + "/" + remote + "/" + branch + "/" + config
                    if not clearOldBuild(bp):
                        print "ERROR: clear old build failed for " + buildPath + "," + remote + "," + branch
                        continue;
                    if not createBuildFolder(bp):
                        print "ERROR: create build folder failed for " + buildPath + "," + remote + "," + branch
                        continue
                    if not configureBuild(repoPath, bp, config):
                        print "ERROR: configure failed for " + buildPath + "," + remote + "," + branch
                        continue
                    if not compileBuild(bp):
                        print "ERROR: build failed for " + buildPath + "," + remote + "," + branch
                        continue

                    # TODO: Figure out which test to run
                    #print "    run tests (TODO, TODO, TODO)"

        else:
            print "ERROR: Remote " + remote + " and/or branch " + branch + " is not available in repositroy"
            print "ERROR: Can not build job " + remote + "/" + branch
            errors = True

if errors:
    print "Erros during build"
else:
    print "All builds succedded"
