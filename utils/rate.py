import argparse
import kafka3
import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='rate.py', description='Measure the rate average at which a topic is being published')
    parser.add_argument('--msgbroker', required=True, help='Specify the message broker <host:port>')
    parser.add_argument('--topic', required=True, help='Specify topic')
    parser.add_argument('--window', type=int, default=1000, help='Specify the averaging window')
    args = parser.parse_args()

    consumer = kafka3.KafkaConsumer(bootstrap_servers=args.msgbroker)
    consumer.subscribe(args.topic)

    window = args.window
    msgs = []

    i = 0
    t0 = time.time()
    try:
        for msg in consumer:
            t = time.time()
            if len(msgs) < window:
                msgs.append(t)
                f = msgs[0]
            else:
                msgs[i] = t
                i = (i + 1) % window
                f = msgs[i]
            if t - t0 >= 1 and f != t:
                print(f'Average rate: {len(msgs) / (t - f):.2f} messages per second')
                t0 = t
    except KeyboardInterrupt:
        pass
