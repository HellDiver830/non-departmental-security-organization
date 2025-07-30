// Глобальные переменные
let globe;           // объект глобуса
let lastTooltip = null;  // последняя отображённая подсказка (Tippy) на глобусе

// Функция заполнения таблиц данными из объекта tables
function populateTables(tables) {
    // tables содержит три ключа: Employees, Objects, Expenses, каждый - массив объектов-строк
    const empFields = ["ID", "FullName", "BirthDate", "HealthClass", "Role", "Equipment", "PatrolHistory", "Warnings"];
    const objFields = ["ID", "ObjName", "Lat", "Lng", "Criticality", "IncidentHistory", "Rating"];
    const expFields = ["ID", "Date", "Item", "Quantity", "Cost", "AssignedTo"];

    // Заполнение таблицы сотрудников
    const empBody = document.querySelector("#employeesTable tbody");
    empBody.innerHTML = "";  // очистить на случай обновления
    tables.Employees.forEach(emp => {
        const tr = document.createElement("tr");
        empFields.forEach(field => {
            const td = document.createElement("td");
            // Вставляем текст (если значение null, вставляем пустую строку)
            td.textContent = (emp[field] !== null ? emp[field] : "");
            if (field !== "ID") {
                td.contentEditable = "true";  // ID не редактируется
            }
            // Сохраняем информацию о месте хранения
            td.dataset.table = "Employees";
            td.dataset.field = field;
            td.dataset.id = emp["ID"];
            td.dataset.old = td.textContent;  // исходное значение, для отката при ошибке
            // Назначаем обработчик ухода фокуса (blur)
            td.addEventListener("blur", onCellBlur);
            tr.appendChild(td);
        });
        empBody.appendChild(tr);
    });

    // Заполнение таблицы объектов
    const objBody = document.querySelector("#objectsTable tbody");
    objBody.innerHTML = "";
    tables.Objects.forEach(obj => {
        const tr = document.createElement("tr");
        objFields.forEach(field => {
            const td = document.createElement("td");
            td.textContent = (obj[field] !== null ? obj[field] : "");
            if (field !== "ID") td.contentEditable = "true";
            td.dataset.table = "Objects";
            td.dataset.field = field;
            td.dataset.id = obj["ID"];
            td.dataset.old = td.textContent;
            td.addEventListener("blur", onCellBlur);
            tr.appendChild(td);
        });
        objBody.appendChild(tr);
    });

    // Заполнение таблицы расходов
    const expBody = document.querySelector("#expensesTable tbody");
    expBody.innerHTML = "";
    tables.Expenses.forEach(exp => {
        const tr = document.createElement("tr");
        expFields.forEach(field => {
            const td = document.createElement("td");
            td.textContent = (exp[field] !== null ? exp[field] : "");
            if (field !== "ID") td.contentEditable = "true";
            td.dataset.table = "Expenses";
            td.dataset.field = field;
            td.dataset.id = exp["ID"];
            td.dataset.old = td.textContent;
            td.addEventListener("blur", onCellBlur);
            tr.appendChild(td);
        });
        expBody.appendChild(tr);
    });

    // Обновляем точки на глобусе после загрузки данных
    updateGlobePoints(tables.Employees, tables.Objects);
}

// Обработчик события blur на ячейке таблицы (завершение редактирования)
function onCellBlur(event) {
    const td = event.target;
    const table = td.dataset.table;
    const field = td.dataset.field;
    const id = Number(td.dataset.id);
    const oldVal = td.dataset.old;
    const newVal = td.textContent;
    if (newVal === oldVal) {
        return; // значение не изменилось, ничего не делаем
    }
    // Отправка запроса на обновление в Python
    eel.update_record(table, id, field, newVal)((result) => {
        if (result !== "OK") {
            // Если ошибка - уведомляем и откатываем значение
            alert(result);
            td.textContent = oldVal;
        } else {
            // Обновляем сохранённое старое значение на новое
            td.dataset.old = newVal;
        }
    });
}

// Инициализация глобуса
function initGlobe() {
    globe = new Globe(document.getElementById('globeViz'))
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')  // текстура тёмной земли
        .pointAltitude(0.02)   // высота столбика точки (относительно радиуса земли)
        .pointRadius(0.4)      // радиус основания точки (в градусах)
        .pointColor(p => p.type === 'employee' ? 'red' : 'blue')  // цвет: красный для сотрудников, синий для объектов
        .pointsData([]);       // пока пусто, данные загрузим позже

    // Обработчик клика по точке на глобусе
    globe.onPointClick((point, event) => {
        // Формируем содержимое всплывающего окна
        let content = "";
        if (point.type === 'employee') {
            content = `<strong>Сотрудник ${point.id}</strong><br>${point.name}<br>Роль: ${point.role}`;
        } else if (point.type === 'object') {
            content = `<strong>Объект ${point.id}</strong><br>${point.name}<br>Критичность: ${point.criticality}`;
        }
        // Если уже есть открытая подсказка, уничтожаем её
        if (lastTooltip) {
            lastTooltip.destroy();
            lastTooltip = null;
        }
        // Создаём новую подсказку на координатах клика
        const tip = tippy(document.body, {
            content: content,
            allowHTML: true,
            trigger: 'manual',
            theme: 'light',       // используем тему 'light', которую мы переопределили стилями (будет тёмной)
            placement: 'right',   // позиция (относительно переданной точки)
            getReferenceClientRect: () => ({
                width: 0,
                height: 0,
                top: event.clientY,
                bottom: event.clientY,
                left: event.clientX,
                right: event.clientX
            })
        });
        // tip - массив из одного элемента (инстанс подсказки)
        lastTooltip = tip[0];
        lastTooltip.show();
    });
}

// Обновление данных точек на глобусе на основе списков сотрудников и объектов
function updateGlobePoints(employees, objects) {
    const points = [];
    // Добавляем точки для сотрудников (с случайными координатами)
    employees.forEach(emp => {
        const lat = Math.random() * 140 - 70;    // случайная широта в диапазоне [-70, 70] для распределения
        const lng = Math.random() * 360 - 180;   // случайная долгота [-180, 180]
        points.push({
            type: 'employee',
            id: emp.ID,
            name: emp.FullName,
            role: emp.Role,
            criticality: null,
            lat: lat,
            lng: lng
        });
    });
    // Добавляем точки для объектов (с данными координатами)
    objects.forEach(obj => {
        points.push({
            type: 'object',
            id: obj.ID,
            name: obj.ObjName,
            role: null,
            criticality: obj.Criticality,
            lat: obj.Lat,
            lng: obj.Lng
        });
    });
    // Обновляем данные точек на глобусе
    globe.pointsData(points);
}

// Отправка текстового сообщения (нажатие Enter или кнопки "Отправить")
function sendUserQuery() {
    const input = document.getElementById("userInput");
    const query = input.value.trim();
    if (!query) return;
    appendMessage(query, "user");    // отобразить сообщение в чате от пользователя
    input.value = "";               // очистить поле ввода
    // Вызвать Python-функцию ассистента и обработать ответ
    eel.handle_query(query)((response) => {
        if (response) {
            appendMessage(response, "assistant");
        }
    });
}

// Добавление сообщения в окно чата
function appendMessage(text, sender) {
    const chatLog = document.getElementById("chatLog");
    const msgDiv = document.createElement("div");
    msgDiv.className = sender;
    if (sender === "user") {
        msgDiv.textContent = "Вы: " + text;
    } else {
        msgDiv.textContent = "Ассистент: " + text;
    }
    chatLog.appendChild(msgDiv);
    // Прокрутить чат вниз, чтобы было видно новое сообщение
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Инициализация голосового ввода
function startVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Ваш браузер не поддерживает Web Speech API для распознавания речи.");
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "ru-RU";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        appendMessage(transcript, "user");
        eel.handle_query(transcript)((response) => {
            if (response) {
                appendMessage(response, "assistant");
            }
        });
    };
    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
    };
    recognition.start();
}

// Установка обработчиков событий после загрузки DOM
window.addEventListener("DOMContentLoaded", () => {
    initGlobe();  // инициализируем глобус
    // Загрузка данных из Python и заполнение таблиц
    eel.get_all_data()(populateTables);
    // Установка обработчиков для кнопок и поля ввода
    document.getElementById("sendBtn").addEventListener("click", sendUserQuery);
    document.getElementById("userInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendUserQuery();
        }
    });
    document.getElementById("voiceBtn").addEventListener("click", startVoiceRecognition);
});
