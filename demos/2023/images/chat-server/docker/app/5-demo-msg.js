var msg = {
  // (A) HELPER - AJAX FETCH
  ajax : (data, after) => {
    // (A1) FORM DATA
    let form = new FormData();
    for (const [k,v] of Object.entries(data)) { form.append(k, v); }

    // (A2) FETCH
    fetch("3-ajax-msg.php", { method:"POST", body:form })
    .then(res => res.text())
    .then(txt => after(txt))
    .catch(err => console.error(err));
  },

  // (B) SHOW MESSAGES
  uid : null,  // current selected user
  show : uid => {
    // (B1) SET SELECTED USER ID
    msg.uid = uid;

    // (B2) GET HTML ELEMENTS
    let hForm = document.getElementById("uSend"),
        hTxt = document.getElementById("mTxt"),
        hUnread = document.querySelector(`#usr${uid} .uUnread`),
        hMsg = document.getElementById("uMsg");

    // (B3) SET SELECTED USER
    for (let r of document.querySelectorAll(".uRow")) {
      if (r.id=="usr"+uid) { r.classList.add("now"); }
      else { r.classList.remove("now"); }
    }

    // (B4) SHOW MESSAGE FORM
    hForm.style.display = "flex";
    hTxt.value = "";
    hTxt.focus();

    // (B5) AJAX LOAD MESSAGES
    hMsg.innerHTML = "";
    msg.ajax({
      req : "show",
      uid : uid
    }, txt => {
      hMsg.innerHTML = txt;
      hUnread.innerHTML = 0;
    });
  },

  // (C) SEND MESSAGE
  send : () => {
    let hTxt = document.getElementById("mTxt");
    msg.ajax({
      req : "send",
      to : msg.uid,
      msg : hTxt.value
    }, txt => {
      if (txt == "OK") {
        msg.show(msg.uid);
        hTxt.value = "";
      } else { alert(txt); }
    });
    return false;
  }
};