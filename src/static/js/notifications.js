// Notificações para utili&tal

// Contador de notificações não lidas
let notificationCount = 0;
let notificationCheckInterval = 60000; // 1 minuto em milissegundos

// Função para buscar contagem de notificações não lidas
function fetchNotificationCount() {
    fetch('/notifications/unread-count')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.count);
        })
        .catch(error => {
            console.error('Erro ao buscar notificações:', error);
        });
}

// Função para atualizar o badge de notificações
function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-count');
    if (badge) {
        notificationCount = count;
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
            
            // Mostrar notificação pop-up se houver novas notificações
            if (Notification.permission === "granted") {
                showDesktopNotification();
            } else if (Notification.permission !== "denied") {
                Notification.requestPermission().then(permission => {
                    if (permission === "granted") {
                        showDesktopNotification();
                    }
                });
            }
        } else {
            badge.textContent = '';
            badge.style.display = 'none';
        }
    }
}

// Função para mostrar notificação desktop
function showDesktopNotification() {
    if (notificationCount > 0) {
        const title = 'utili&tal Tarefas';
        const options = {
            body: `Você tem ${notificationCount} notificação(ões) não lida(s)`,
            icon: '/static/images/utilietal_logo.jpg'
        };
        
        const notification = new Notification(title, options);
        
        notification.onclick = function() {
            window.focus();
            window.location.href = '/notifications/';
            this.close();
        };
        
        // Fechar automaticamente após 5 segundos
        setTimeout(() => {
            notification.close();
        }, 5000);
    }
}

// Iniciar verificação de notificações quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verificar notificações imediatamente
    fetchNotificationCount();
    
    // Configurar verificação periódica
    setInterval(fetchNotificationCount, notificationCheckInterval);
    
    // Solicitar permissão para notificações desktop
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
});

// Função para marcar notificação como lida via AJAX
function markNotificationAsRead(notificationId, element) {
    fetch(`/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ ajax: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Atualizar UI
            if (element) {
                element.classList.add('read');
                const badge = element.querySelector('.notification-badge');
                if (badge) badge.remove();
            }
            // Atualizar contador
            fetchNotificationCount();
        }
    })
    .catch(error => {
        console.error('Erro ao marcar notificação como lida:', error);
    });
}

// Função para marcar todas notificações como lidas
function markAllNotificationsAsRead() {
    fetch('/notifications/read-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ ajax: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Atualizar UI - marcar todas como lidas
            document.querySelectorAll('.notification-item').forEach(item => {
                item.classList.add('read');
                const badge = item.querySelector('.notification-badge');
                if (badge) badge.remove();
            });
            // Atualizar contador
            fetchNotificationCount();
        }
    })
    .catch(error => {
        console.error('Erro ao marcar todas notificações como lidas:', error);
    });
}
