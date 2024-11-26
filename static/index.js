let q = document.getElementById("q");
let group = document.getElementById("group");

async function loadVideos(first_time) {
    if (first_time) {
        q.value = "";
        group.value = "All";
    }
    let responce = await fetch("/search?q=" + encodeURIComponent(q.value) + "&group=" + encodeURIComponent(group.value));
    let data = await responce.text();
    document.getElementById("videos").innerHTML = data;

    // add event listener to all name-boxes
    document.querySelectorAll(".name-box").forEach(el => {
        el.addEventListener("click", ev => {
            const videoId = el.getAttribute("video-id");
            window.location.href = `/video/${videoId}/edit`;
        });
    });
}

loadVideos(true);
q.addEventListener("input", () => loadVideos(false));
group.addEventListener("input", () => loadVideos(false));
