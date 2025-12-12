pipeline {
  agent any

  parameters {
    string(name: 'GNS3_VM_SSH_IP', defaultValue: '', description: 'IP/hostname of the remote GNS3 VM')
    string(name: 'PROJECT_NAME', defaultValue: 'OT-Industrial-Topology', description: 'GNS3 project name')
  }

  environment {
    ANSIBLE_HOST_KEY_CHECKING = 'False'
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
    PYTHONUNBUFFERED = '1'
  }

  stages {

    stage('Validate parameters') {
      steps {
        script {
          if (!params.GNS3_VM_SSH_IP?.trim()) { error("GNS3_VM_SSH_IP is required") }
          if (!params.PROJECT_NAME?.trim())   { error("PROJECT_NAME is required") }
        }
      }
    }

    stage('Checkout') {
      steps { checkout scm }
    }

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
repo_root=/opt/ot-industrial-topology
EOF
        '''
      }
    }

    stage('Bootstrap Python + Install Ansible') {
      steps {
        sh '''
          set -e

          echo "== Python =="
          command -v python3 >/dev/null 2>&1 || { echo "python3 not found on Jenkins agent"; exit 1; }
          python3 --version

          # ---- Ensure pip exists ----
          if ! python3 -m pip --version >/dev/null 2>&1; then
            echo "pip not found. Attempting python3 -m ensurepip ..."
            if python3 -m ensurepip --user >/dev/null 2>&1; then
              echo "ensurepip succeeded."
            else
              echo "ensurepip failed. Trying OS package install (Debian/Ubuntu) ..."
              if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update -y
                sudo apt-get install -y python3-pip
              else
                echo "No ensurepip and no apt-get available. Falling back to get-pip.py ..."
                if command -v curl >/dev/null 2>&1; then
                  curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
                elif command -v wget >/dev/null 2>&1; then
                  wget -qO /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
                else
                  echo "Neither curl nor wget available to download get-pip.py"
                  exit 1
                fi
                python3 /tmp/get-pip.py --user
              fi
            fi
          fi

          # ---- Upgrade pip + install Ansible ----
          python3 -m pip install --user --upgrade pip
          python3 -m pip install --user "ansible>=9.0.0" "requests>=2.31.0"

          # Put user-base bin on PATH so ansible-playbook is found
          USER_BASE="$(python3 -c 'import site; print(site.USER_BASE)')"
          export PATH="$USER_BASE/bin:$PATH"

          echo "== Ansible =="
          ansible --version
          ansible-galaxy collection install community.docker
        '''
      }
    }

    stage('Deploy (Ansible -> GNS3 VM)') {
      steps {
        withCredentials([
          sshUserPrivateKey(credentialsId: 'GNS3_VM_SSH_KEY',
                            keyFileVariable: 'SSH_KEYFILE',
                            usernameVariable: 'SSH_USER')
        ]) {
          sh '''
            set -e

            USER_BASE="$(python3 -c 'import site; print(site.USER_BASE)')"
            export PATH="$USER_BASE/bin:$PATH"

            ansible-playbook -i ansible/inventory.ini ansible/site.yml \
              -e ansible_user=${SSH_USER} \
              --private-key ${SSH_KEYFILE}
          '''
        }
      }
    }
  }

  post {
    success {
      echo "✅ Deployed. HMI: http://10.10.30.10:8000/ (from OT network)"
    }
    failure {
      echo "❌ Deploy failed — check console output."
    }
  }
}
