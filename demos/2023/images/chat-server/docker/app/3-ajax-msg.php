<?php
if (isset($_POST["req"])) {
  require "2-lib-msg.php";
  switch ($_POST["req"]) {
    // (A) SHOW MESSAGES
    case "show":
      $msg = $_MSG->getMsg($_POST["uid"], $_SESSION["user"]["id"]);
      if (count($msg)>0) { foreach ($msg as $m) {
        $out = $m["user_from"] == $_SESSION["user"]["id"]; ?>
        <div class="mRow <?=$out?"mOut":"mIn"?>">
          <div class="mDate"><?=$m["date_send"]?></div>
        </div>
        <div class="mRow <?=$out?"mOut":"mIn"?>"><div class="mRowMsg">
          <div class="mSender"><?=$m["user_name"]?></div>
          <div class="mTxt"><?=$m["message"]?></div>
        </div></div>
      <?php }}
      break;

    // (B) SEND MESSAGE
    case "send":
      echo $_MSG->send($_SESSION["user"]["id"], $_POST["to"], $_POST["msg"])
        ? "OK" : $_MSG->error ;
      break;
}}