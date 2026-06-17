import 'package:dongle/src/cli.dart';

void main(List<String> arguments) {
  if (arguments.isEmpty) {
    cmdIntro();
    return;
  }

  String cmd = arguments.first;
  var restArgs = arguments.sublist(1);

  if (cmd == 'pick') {
    cmdPick(restArgs);
  } else if (cmd == 'scan') {
    cmdScan(restArgs);
  } else if (cmd == 'list') {
    cmdList(restArgs);
  } else if (cmd == 'root') {
    cmdRoot();
  } else if (cmd == 'recent') {
    cmdRecent();
  } else if (cmd == 'init') {
    cmdInit(restArgs);
  } else if (cmd == 'doctor') {
    cmdDoctor();
  } else if (cmd == 'version' || cmd == '--version' || cmd == '-v') {
    cmdVersion();
  } else if (cmd == 'help' || cmd == '--help' || cmd == '-h') {
    cmdIntro();
  } else {
    if (cmd.startsWith('-')) {
      cmdIntro();
    } else {
      cmdPick(['--query', cmd, ...restArgs]);
    }
  }
}
