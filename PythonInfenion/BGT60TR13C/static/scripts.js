const socket = io();

function runScript(script) {
    $.get(`/${script}`, function(data) {
        $('#message').html(`<p>${data.message}</p>`);
        if(data.status === 'success') {
            $('#message').css('color', 'green');
        } else if(data.status === 'error') {
            $('#message').css('color', 'red');
        } else {
            $('#message').css('color', 'orange');
        }
    });
}

socket.on('connect', function() {
    console.log('Connected to server');
    socket.emit('request_plot');
});

socket.on('plot_data', function(data) {
    $('#plot').attr('src', 'data:image/png;base64,' + btoa(data.image));
});
