// home.js -- progress-bar script for home.html.

function move(num_users, num_tweets, num_processors) {
    var elem = document.getElementById("myBar");
    var width = 1;
    var id = setInterval(frame, 10);
    function frame() {
        if (width >= 100) {
            clearInterval(id);
        } else {
            // width = width + 0.02;
            width = width + (0.07 * num_processors) / (num_users * num_tweets);
            elem.style.width = width + '%';
        }
    }
}

$(document).ready(function() {
	document.getElementById("submit-single").addEventListener("click", function(e) {
    	move(1, parseFloat(document.getElementById("tweets-num-single").value), parseFloat(document.getElementById("processor-count-single").value));
	});
	document.getElementById("submit-bulk").addEventListener("click", function(e) {
    	move(parseFloat(document.getElementById("users-num").value), parseFloat(document.getElementById("tweets-num-bulk").value), parseFloat(document.getElementById("processor-count-bulk").value));
	});
});

