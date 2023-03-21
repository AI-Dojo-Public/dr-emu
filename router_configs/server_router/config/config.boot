system {
    host-name "vyos"
    login {
        user vyos {
            authentication {
                encrypted-password "$6$QxPS.uk6mfo$9QBSo8u1FkH16gMyAVhus6fU3LOzvLR9Z9.82m3tiHFAxTtIkhaZSWssSgzt4v4dGAL8rhVQxTg0oAG9/q11h/"
                plaintext-password ""
            }
        }
    }
 }
 protocols {
    static {
        route 0.0.0.0/0 {
            next-hop 192.168.50.10 {
            }
        }
    }
}