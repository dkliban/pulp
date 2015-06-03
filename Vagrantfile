# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
 config.vm.box = "humaton/fedora-21-cloud"
 config.vm.host_name = "pulp-devel"
 config.vm.synced_folder "..", "/home/vagrant/devel", type: "nfs", nfs_version: 4, nfs_udp: false
 # By default, Vagrant wants to mount the code in /vagrant with NFSv3, which will fail. Let's
 # explicitly mount the code using NFSv4. We probably won't need to use this, since the above line
 # configures all the code we need for us, but vagrant up will fail without this line.
 config.vm.synced_folder ".", "/vagrant", type: "nfs", nfs_version: 4, nfs_udp: false

 config.vm.provider :libvirt do |domain|
   domain.memory = 2048
   domain.cpus   = 4
 end

 config.vm.provision "shell", inline: "yum install -y dnf"
 config.vm.provision "shell", inline: "dnf upgrade -y"
 config.vm.provision "shell", inline: "sudo -u vagrant bash -e /home/vagrant/devel/pulp/playpen/vagrant-setup.sh"
 config.vm.provision "shell", inline: "sudo systemctl stop mongod"
 config.vm.provision "shell", inline: "mkdir -p /home/vagrant/rs0-{0,1,2}"
 config.vm.provision "shell", inline: "mongod --fork --nojournal --syslog --port 27017 --dbpath /home/vagrant/rs0-0 --replSet rs0"
 config.vm.provision "shell", inline: "mongod --fork --nojournal --syslog --port 27018 --dbpath /home/vagrant/rs0-1 --replSet rs0"
 config.vm.provision "shell", inline: "mongod --fork --nojournal --syslog --port 27019 --dbpath /home/vagrant/rs0-2 --replSet rs0"

end
