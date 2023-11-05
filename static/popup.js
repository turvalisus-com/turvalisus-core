function setMobilePopups(contentContainerSelector) {
    if (Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0) >= 1000) {
        return;
    }

    if (document.querySelector("#top-tip") !== null) {
        document.querySelector('#top-tip').hidden = false;
    }

    const promptOffset = document.querySelector(contentContainerSelector).clientHeight;

    if (document.querySelector(".prompt") !== null) {
        document.querySelector(".prompt").style.marginTop = `${promptOffset}px`;
    }

    if (document.querySelector(".result") !== null) {
        document.querySelector(".result").style.marginTop = `${promptOffset}px`;
    }
}

function dragElement(hook, elmnt) {
    var pos1 = 0,
        pos2 = 0,
        pos3 = 0,
        pos4 = 0;
    hook.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
        elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}
