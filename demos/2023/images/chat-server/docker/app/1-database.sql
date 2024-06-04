-- (A) USERS
CREATE TABLE `users` (
  `user_id` bigint(20) NOT NULL,
  `user_name` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`);

ALTER TABLE `users`
  MODIFY `user_id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;

INSERT INTO `users` (`user_id`, `user_name`) VALUES
  (1, 'Joe Doe'),
  (2, 'Jon Doe'),
  (3, 'Joy Doe');

-- (B) MESSAGES
CREATE TABLE `messages` (
  `user_from` bigint(20) NOT NULL,
  `user_to` bigint(20) NOT NULL,
  `date_send` datetime NOT NULL DEFAULT current_timestamp(),
  `date_read` datetime DEFAULT NULL,
  `message` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `messages`
  ADD PRIMARY KEY (`user_from`, `user_to`, `date_send`),
  ADD KEY `date_read` (`date_read`);