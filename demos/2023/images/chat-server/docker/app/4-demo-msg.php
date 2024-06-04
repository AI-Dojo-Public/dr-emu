<!DOCTYPE html>
<html>
  <head>
    <title>Users List</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="x-demo-msg.css">
    <script src="5-demo-msg.js"></script>
  </head>
  <body>
    <?php
    // (A) GET USERS
    require "2-lib-msg.php";
    $users = $_MSG->getUsers($_SESSION["user"]["id"]); ?>

    <!-- (B) LEFT : USER LIST -->
    <div id="uLeft">
      <!-- (B1) CURRENT USER -->
      <div id="uNow">
        <div><img src="x-girl.png"></div>
        <div><?=$_SESSION["user"]["name"]?></div>
      </div>

      <!-- (B2) USER LIST -->
      <?php foreach ($users as $uid=>$u) { ?>
      <div class="uRow" id="usr<?=$uid?>" onclick="msg.show(<?=$uid?>)">
        <div class="uName"><?=$u["user_name"]?></div>
        <div class="uUnread"><?=isset($u["unread"])?$u["unread"]:0?></div>
      </div>
      <?php } ?>
    </div>

    <!-- (C) RIGHT : MESSAGES LIST -->
    <div id="uRight">
      <!-- (C1) SEND MESSAGE -->
      <form id="uSend" onsubmit="return msg.send()">
        <input type="text" id="mTxt" required>
        <input type="submit" value="Send">
      </form>

       <!-- (C2) MESSAGES -->
       <div id="uMsg"></div>
    </div>
  </body>
</html>