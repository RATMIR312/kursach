// Основные функции для фронтенда

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация
    console.log('Cricket Score System loaded');
});

// Функция для отображения уведомлений
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    document.querySelector('.container').prepend(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// Функция для загрузки данных через API
async function fetchData(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('Error fetching data:', error);
        showAlert(`Error: ${error.message}`, 'error');
        throw error;
    }
}

// Функция для расчета очков (вызывается из calculate.html)
async function calculatePlayerPoints() {
    const playerId = document.getElementById('playerSelect').value;
    const matchId = document.getElementById('matchSelect').value;
    const additionalData = {};
    
    // Сбор дополнительных данных в зависимости от роли игрока
    const playerRole = document.getElementById('playerRole').value;
    if (playerRole === 'batsman') {
        additionalData.fours = document.getElementById('fours').value || 0;
        additionalData.sixes = document.getElementById('sixes').value || 0;
        additionalData.dismissal_type = document.getElementById('dismissalType').value || 'not_out';
    } else if (playerRole === 'bowler') {
        additionalData.overs_bowled = document.getElementById('oversBowled').value || 4;
        additionalData.maidens = document.getElementById('maidens').value || 0;
    }
    
    try {
        const data = {
            player_id: parseInt(playerId),
            match_id: parseInt(matchId),
            ...additionalData
        };
        
        const result = await fetchData('/api/calculate', 'POST', data);
        
        showAlert(`Points calculated: ${result.points} for ${result.player}`, 'success');
        
        // Обновляем историю, если на странице есть таблица истории
        if (typeof updatePointsHistory === 'function') {
            updatePointsHistory();
        }
        
        return result;
    } catch (error) {
        console.error('Calculation failed:', error);
    }
}

// Функция для обновления истории очков
async function updatePointsHistory() {
    try {
        const history = await fetchData('/api/points/history');
        const tbody = document.getElementById('pointsHistory');
        
        if (tbody) {
            tbody.innerHTML = '';
            
            history.forEach(record => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${record.id}</td>
                    <td>${record.player_name}</td>
                    <td>${record.match_info}</td>
                    <td><strong>${record.points}</strong></td>
                    <td>${new Date(record.calculation_date).toLocaleDateString()}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to update history:', error);
    }
}

// Функция для загрузки матчей в выпадающий список
async function loadMatchesForSelect(selectId) {
    try {
        const matches = await fetchData('/api/matches');
        const select = document.getElementById(selectId);
        
        if (select) {
            // Сохраняем текущее значение
            const currentValue = select.value;
            
            // Очищаем опции
            select.innerHTML = '<option value="">Select a match</option>';
            
            // Добавляем новые опции
            matches.forEach(match => {
                const option = document.createElement('option');
                option.value = match.id;
                option.textContent = `${match.team1} vs ${match.team2} - ${match.format}`;
                select.appendChild(option);
            });
            
            // Восстанавливаем выбранное значение, если оно есть
            if (currentValue) {
                select.value = currentValue;
            }
        }
    } catch (error) {
        console.error('Failed to load matches:', error);
    }
}

// Функция для загрузки игроков в выпадающий список
async function loadPlayersForSelect(selectId) {
    try {
        const players = await fetchData('/api/players');
        const select = document.getElementById(selectId);
        
        if (select) {
            // Сохраняем текущее значение
            const currentValue = select.value;
            
            // Очищаем опции
            select.innerHTML = '<option value="">Select a player</option>';
            
            // Добавляем новые опции
            players.forEach(player => {
                const option = document.createElement('option');
                option.value = player.id;
                option.textContent = `${player.name} (${player.role}, ${player.team})`;
                option.dataset.role = player.role; // Сохраняем роль для использования
                select.appendChild(option);
            });
            
            // Восстанавливаем выбранное значение, если оно есть
            if (currentValue) {
                select.value = currentValue;
            }
            
            // Добавляем обработчик изменения для обновления формы в зависимости от роли
            select.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const role = selectedOption.dataset.role;
                
                // Показываем/скрываем дополнительные поля в зависимости от роли
                const batsmanFields = document.getElementById('batsmanFields');
                const bowlerFields = document.getElementById('bowlerFields');
                
                if (batsmanFields) batsmanFields.style.display = role === 'batsman' ? 'block' : 'none';
                if (bowlerFields) bowlerFields.style.display = role === 'bowler' ? 'block' : 'none';
                
                // Обновляем скрытое поле с ролью
                const roleField = document.getElementById('playerRole');
                if (roleField) {
                    roleField.value = role || '';
                }
            });
        }
    } catch (error) {
        console.error('Failed to load players:', error);
    }
}
