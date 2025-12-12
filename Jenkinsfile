pipeline {
  agent any

  parameters {
    string(name: 'GNS3_VM_SSH_IP', defaultValue: '', description: 'IP/hostname of the remote GNS3 VM')
    string(name: 'PROJECT_NAME', defaultValue: 'OT-Labshock-OT', description: 'GNS3 project name')
  }

  environment {
    ANSIBLE_HOST_KEY_CHECKING = 'False'
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
  }

  stages {
    stage('Validate parameters') {
      steps {
        script {
          if (!params.GNS3_VM_SSH_IP?.trim()) { error("GNS3_VM_SSH_IP is required") }
        }
      }
    }

    stage('Checkout') { steps { checkout scm } }

    stage('Prepare runtime config') {
      steps {
        sh '''
          set -e
          mkdir -p gns3 ansible

          cat > gns3/config.yaml <<EOF
gns3:
  url: "http://127.0.0.1:3080"
  project_name: "${PROJECT_NAME}"
  compute_id: "local"
  ot_switch_name: "OT-SW"
  ot_subnet_cidr: "10.10.30.0/24"

images:
  plc_image: "plc_pump:latest"
  gateway_image: "ot_gateway:latest"

gateway:
  name: "OT-Gateway"
  ip_cidr: "10.10.30.10/24"
  gw: ""

cells:
  count: 10
  base_ip: 100
  stride: 10
EOF

          cat > ansible/inventory.ini <<EOF
[gns3vm]
gns3vm ansible_host=${GNS3_VM_SSH_IP}

[all:vars]
ansible_user=gns3
ansible_python_interpreter=/usr/bin/python3
repo_root=/opt/ot-labshock
EOF
        '''
      }
    }

    stage('Install Ansible on Jenkins agent') {
      steps {
        sh '''
          set -e
          python3 -m pip install --upgrade pip
          python3 -m pip install "ansible>=9.0.0" "requests>=2.31.0"
          ansible-galaxy collection install community.docker
        '''
      }
    }

    stage('Deploy (Ansible -> GNS3 VM)') {
      steps {
        withCredentials([
          sshUserPrivateKey(credentialsId: 'GNS3_VM_SSH_KEY', keyFileVariable: 'SSH_KEYFILE', usernameVariable: 'SSH_USER')
        ]) {
          sh '''
            set -e
            ansible-playbook -i ansible/inventory.ini ansible/site.yml               -e ansible_user=${SSH_USER}               --private-key ${SSH_KEYFILE}
          '''
        }
      }
    }
  }

  post {
    success { echo "✅ Deployed. HMI: http://10.10.30.10:8000/ (from OT network)" }
    failure { echo "❌ Deploy failed — check console output." }
  }
}
