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
}

loadVideos(true);
q.addEventListener("input", () => loadVideos(false));
group.addEventListener("input", () => loadVideos(false));

