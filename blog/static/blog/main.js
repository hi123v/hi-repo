document.addEventListener('DOMContentLoaded', function() {
    var studentButton = document.getElementById('studentButton');
    var teacherButton = document.getElementById('teacherButton');
    var parentButton = document.getElementById('parentButton');
    var loginForm = document.getElementById('loginForm');

    function showLoginForm() {
        loginForm.style.display = 'block';
        studentButton.style.display = 'none';
        teacherButton.style.display = 'none';
        parentButton.style.display = 'none';
    }

    studentButton.addEventListener('click', showLoginForm);
    teacherButton.addEventListener('click', showLoginForm);
    parentButton.addEventListener('click', showLoginForm);
});