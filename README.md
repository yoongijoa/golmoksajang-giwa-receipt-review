# 골목사장 · GIWA 영수증 검증

두 매장이 바우처 결제를 확인한 뒤, 보관한 영수증이 당시 기록과 같은지 가상 데이터로 재현합니다. 영수증에 소금값(salt)을 포함해 SHA-256 지문을 계산하고, GIWA Sepolia의 `ReceiptRegistry` 컨트랙트에 32바이트 지문을 등록했습니다. 지문이 일치하면 보관한 영수증 내용이 해당 기록과 일치한다는 뜻입니다. 이는 영수증 내용의 대조이며, 실제 거래 당사자의 신원을 증명하지 않습니다.

## 심사용 컨트랙트와 재현 방법

- [Verified 컨트랙트 소스와 ABI](https://sepolia-explorer.giwa.io/address/0xda0b98c4b8BEbbAD5af3b9CdE32A71f01767797B?tab=contract)
- [가상 영수증 한 건의 기록 거래](https://sepolia-explorer.giwa.io/tx/0x4536a056b8e05e2ecda6ca546081e366e680920d86a5fec6fdb4ae60edc1cdb2)
- [컨트랙트 배포 거래](https://sepolia-explorer.giwa.io/tx/0x66a1ad292e87086848aeda06e621a35274ae27c8d769b6c054cf924435068cc2) · [Solidity 소스](contracts/ReceiptRegistry.sol)

저장소를 내려받은 뒤 Python과 curl이 있는 터미널에서 실행하세요. 지갑, 로그인, 테스트 ETH 없이 조회할 수 있습니다.

```shell
python review.py contract
```

이 명령은 실제 거래의 성공 여부와 `ReceiptRecorded` 이벤트를 확인한 뒤, 컨트랙트의 `recorded(bytes32)`를 두 번 조회합니다. 1,000원 예제는 `recorded`, 금액만 10,000원으로 바꾸면 `not recorded`가 출력됩니다.

등록 함수 `record(bytes32)`는 배포 지갑만 호출할 수 있습니다. 같은 지문의 중복 등록과 빈 지문은 거부합니다. 누구나 등록 여부를 조회할 수 있습니다. 컴파일 설정은 Solidity 0.8.28+commit.7893614a, optimizer 200 runs, EVM Paris입니다.

## 1. 가상 영수증으로 바로 확인하기

Python 3.10 이상에서 아래 명령을 실행하세요. 이 단계는 인터넷, 지갑, 외부 패키지 없이 동작합니다.

```shell
git clone https://github.com/yoongijoa/golmoksajang-giwa-receipt-review.git
cd golmoksajang-giwa-receipt-review
python review.py demo
```

`example-receipt.json`은 설명을 위해 만든 1,000원짜리 가상 영수증입니다. 예제를 그대로 계산한 결과와 금액만 10,000원으로 바꾼 결과를 각각 고정된 예제 지문과 비교합니다.

```text
1,000 KRW: MATCH 0x8a2ab8e5e1ebb5effdc941ce01867dae932f76eaab1ea920bcb3e77ba96fb877
10,000 KRW: MISMATCH ...
```

고정된 예제 지문과의 대조는 오프라인 시연입니다. 실제 컨트랙트 기록과의 대조에는 위의 `python review.py contract`를 사용하세요.

## 2. 이전 파일럿 재현 · 자기 지갑으로 지문 전송 (선택)

Python과 curl이 설치된 터미널에서, GIWA Sepolia 테스트 ETH가 소량 들어 있는 일회용 테스트 지갑을 준비하세요. 체인 ID는 91342입니다. 아래 명령을 실행하면 터미널이 테스트 지갑 키를 숨김 입력으로 받습니다. 키는 파일에 저장하지 않습니다.

```shell
python -m pip install -r requirements.txt
python review.py publish
```

프로그램은 체인 ID를 확인하고 자기 지갑으로 금액 0인 트랜잭션을 보냅니다. 영수증 지문이 입력 데이터에 담기며 테스트넷 수수료가 듭니다. 화면에 출력되는 트랜잭션 해시와 공개 지갑 주소를 보관하세요. 재실행하면 같은 작업 폴더의 전송 기록을 사용해 동일 트랜잭션을 조회하거나 재전송합니다.

## 3. 이전 파일럿의 자기 지갑 전송 기록 대조하기

다음 명령의 두 인자를 2단계에서 출력된 실제 값으로 바꾸세요. 조회에는 Python, curl, 인터넷 연결만 필요합니다.

```shell
python review.py verify TRANSACTION_HASH PUBLIC_SIGNER_ADDRESS
```

검증 코드는 트랜잭션 성공, 블록 해시 일치, 후속 블록 생성, 발신·수신 주소, 전송 금액 0, 입력 데이터와 영수증 지문의 일치를 검사합니다. 금액만 바꾼 영수증의 지문이 다르면 마지막에 `originalMatches: true`, `alteredMatches: false`가 출력됩니다. 블록 확인 대기 시간이 지나면 같은 인자로 다시 조회할 수 있습니다.

## 코드와 데이터 범위

- `receipt.py` — 골목사장 테스트 배치에서 추린 영수증 직렬화·해시 계산, 테스트넷 전송, 블록 및 영수증 대조 함수입니다.
- `review.py` — 심사위원이 가상 영수증으로 위 함수를 실행할 수 있게 만든 명령행 예제입니다.
- 가상 영수증에는 재현을 위한 고정 salt가 들어 있습니다. 원래 배치는 영수증마다 임의의 salt를 생성합니다. 체인에는 지문과 일반 트랜잭션 정보가 공개됩니다. 영수증 원문은 체인에 전송하지 않습니다.
- 이 예제는 결제 완료 이후부터 시작합니다. 실제 가게, 거래 데이터, 업무용 지갑, 서비스 DB 연결 없이 실행할 수 있습니다.
