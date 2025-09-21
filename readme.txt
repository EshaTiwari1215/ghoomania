app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'alishapanday69@gmail.com'

app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

base.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Ghoomania{% endblock %}</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap" rel="stylesheet"/>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/7.1.0/mdb.min.css" rel="stylesheet"/>
    <style>
      body {
        background-color: #f0f2f5;
        padding-top: 70px;
      }
      .main-body {
        display: flex;
        justify-content: space-between;
        padding: 1rem;
      }
      .left-sidebar, .right-sidebar {
        position: sticky;
        top: 80px;
        height: calc(100vh - 80px);
        flex-basis: 24%;
        overflow-y: auto;
      }
      .center-feed {
        flex-basis: 48%;
        max-width: 700px;
      }
      .left-sidebar::-webkit-scrollbar, .right-sidebar::-webkit-scrollbar {
        width: 0px;
        background: transparent;
      }
      .list-group-item {
        border: none;
        padding: 0.75rem 0.5rem;
      }
      .story-text {
        position: relative;
        overflow: hidden;
        transition: max-height 0.5s ease-in-out;
      }
      .story-collapsed {
        max-height: 5em;
      }
      .story-expanded {
        max-height: 1000px;
      }
      .read-more-btn {
        font-weight: bold;
        cursor: pointer;
        color: #65676b;
      }
      .action-btn.recommended {
        color: #0866FF !important;
        font-weight: bold;
      }
      .action-btn.bucketed {
        color: #42B72A !important;
        font-weight: bold;
      }
      .alert-code {
        background-color: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
      }
      .alert-danger {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
      }
       .alert-warning {
        background-color: #fff3cd;
        border-color: #ffeeba;
        color: #856404;
      }
       .alert-success {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
      }
    </style>
</head>
<body>
    <main class="container-fluid">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category if category != 'message' else 'info' }} fixed-top text-center" role="alert" style="top: 60px; z-index: 2000;">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>
    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/mdb-ui-kit/7.1.0/mdb.umd.min.js"></script>
    <script>
      document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.read-more-btn').forEach(button => {
          button.addEventListener('click', function(event) {
            event.preventDefault();
            const targetId = this.getAttribute('data-target');
            const storyText = document.querySelector(targetId);
            if (!storyText) return;
            if (storyText.classList.contains('story-collapsed')) {
              storyText.classList.remove('story-collapsed');
              storyText.classList.add('story-expanded');
              this.textContent = 'Read Less';
            } else {
              storyText.classList.remove('story-expanded');
              storyText.classList.add('story-collapsed');
              this.textContent = 'Read More';
            }
          });
        });

        document.querySelectorAll('.recommend-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const spotId = this.dataset.spotId;
                fetch(`/recommend/${spotId}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(data.error);
                            return;
                        }
                        const recCountSpan = document.getElementById(`rec-count-${spotId}`);
                        const potentialCoinsDiv = document.getElementById(`potential-coins-${spotId}`);
                        if(recCountSpan) recCountSpan.textContent = data.count;
                        this.classList.toggle('recommended', data.recommended);
                        if(potentialCoinsDiv){
                          const newPotentialCoins = data.count * 5;
                          potentialCoinsDiv.innerHTML = `<i class="fas fa-coins me-1"></i> ${newPotentialCoins} Coins on Visit`;
                        }
                    });
            });
        });

        document.querySelectorAll('.bucket-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const spotId = this.dataset.spotId;
                const buttonText = this.querySelector('span');
                fetch(`/bucket/${spotId}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(data.error);
                            return;
                        }
                        this.classList.toggle('bucketed', data.bucketed);
                        if(buttonText) buttonText.textContent = data.bucketed ? 'In Bucket' : 'Add to Bucket';
                    });
            });
        });
        
        const qrScannerModal = document.getElementById('qrScannerModal');
        if (qrScannerModal) {
            const html5QrcodeScanner = new Html5Qrcode("qr-reader");
            
            const qrCodeSuccessCallback = (decodedText, decodedResult) => {
                html5QrcodeScanner.stop().then((ignore) => {
                    window.location.href = decodedText;
                }).catch((err) => {
                    console.error("Failed to stop scanner", err);
                });
            };

            const config = { fps: 10, qrbox: { width: 250, height: 250 } };

            qrScannerModal.addEventListener('shown.mdb.modal', () => {
                html5QrcodeScanner.start({ facingMode: "environment" }, config, qrCodeSuccessCallback);
            });

            qrScannerModal.addEventListener('hidden.mdb.modal', () => {
                html5QrcodeScanner.stop().catch(err => {
                    // Ignore errors if the scanner is already stopped.
                });
            });
        }
      });
    </script>
</body>
</html>

