
#### <In korea>
## 요약

Django_replicated는 다소간 자동 마스터 - 슬레이브 복제를 지원하도록 설계된 Django[database router] [1]입니다.
사용자가 데이터베이스를 읽거나 쓸 의도가있는 내부 상태를 유지합니다. 이 상태에 따라 모든 SQL 조작에 대해 자동으로
올바른 데이터베이스 (master or slave)를 사용합니다.

[1]: http://docs.djangoproject.com/en/dev/topics/db/multi-db/#topics-db-multi-db-routing


## 설치

1. "python setup.py install"을 사용하여 django_replicated 배포판을 설치하십시오.

1. 기본 'django_replicated'설정 가져 오기를 'settings.py`에 추가하십시오 :

        from django_replicated.settings import *

1. settings.py에서 마스터 및 슬레이브 데이터베이스를 표준 방식으로 구성하십시오.

        database {
            'default': {
                # ENGINE, HOST, etc.
            },
            'slave1': {
                # ENGINE, HOST, etc.
            },
            'slave2': {
                # ENGINE, HOST, etc.
            },
        }

1. django_replicated에게 어떤 데이터베이스가 슬레이브인지 가르쳐줍니다 :

        REPLICATED_DATABASE_SLAVES = [ 'slave 1', 'slave 2']

    '기본'데이터베이스는 항상 마스터로 처리됩니다.

1. replication router 구성 :

        DATABASE_ROUTERS = [ 'django_replicated.router.ReplicationRouter']

1. 시간 초과를 구성한 후 사용 가능한 목록에서 데이터베이스를 제외 시키십시오.
    unsuccessful ping:

        REPLICATED_DATABASE_DOWNTIME = 20

    기본 정지 시간 값은 60 초입니다.


## 사용

Django_replicated는 SQL 쿼리를 유형 (insert / update / delete vs. select)뿐만 
아니라 자체의 현재 상태에 따라 다른 데이터베이스로 라우팅합니다.
이것은 단일 논리 조작으로 쓰기와 읽기가 모두 수행되는 상황을 지원하기 위해 수행됩니다.
쓰기 및 읽기가 별도의 데이터베이스를 사용하는 경우 다음과 같은 이유로 인해 결과가 일치하지 않습니다.

- 트랜잭션을 사용할 때 커밋 될 때까지 쓰기 결과가 슬레이브에 전달되지 않습니다.
- 비 트랜잭션 환경에서도 업데이트가 슬레이브에 도달하기 전에 항상 일정한 지연이 있습니다.

Django_replicated는 이러한 논리 연산이 수행하는 작업을 정의하기를 기대합니다 : 
쓰기 / 읽기 또는 읽기만. 그런 다음 순전히 독서 작업에만 슬레이브 데이터베이스를 사용하려고 시도합니다.
이를 정의하는 몇 가지 방법이 있습니다.

### 미들웨어

프로젝트가 GET 요청으로 인해 시스템의 변경을 초래하지 않는 HTTP 원칙 (부작용이 아닌 경우)에 따라 작성된 경우
대부분의 작업은 단순히 미들웨어를 사용하여 수행됩니다.

    MIDDLEWARE_CLASSES = [
        ...
        'django_replicated.middleware.ReplicationMiddleware',
        ...
    ]

미들웨어는 GET 및 HEAD 요청을 처리하는 동안 슬레이브를 사용하고 그렇지 않은 경우 마스터를 사용하도록 복제 상태를 설정합니다.

일반적으로 충분하지만 DB 액세스가 비즈니스 논리에 의해 명시 적으로 제어되지 않는 경우가 있습니다. 
좋은 예는 첫 번째 액세스에서 암시 적으로 세션 생성, 일부 부기 정보 작성, 시스템 내부 어딘가에있는 사용자 계정의 암시 적 등록입니다.
이러한 일은 GET 요청을 포함하여 임의의 시간에 발생할 수 있습니다.

일반적으로 django_replicated는 쓰기 작업을 위해 항상 master 데이터베이스를 사용하여이 문제를 처리합니다. 
이것이 충분하지 않은 경우 (예 : 새로 생성 된 세션이 마스터에서 읽혀 졌는지 확인하려는 경우) 언제든지 Django ORM에
[특정 데이터베이스 사용] [2]을 지시 할 수 있습니다.

[2] : http://docs.djangoproject.com/en/dev/topics/db/multi-db/#manually-selecting-a-database



### 장식

만약 당신의 시스템이 HTTP 요청의 방법에 의존하지 않는다면 쓰기와
read를 사용하면 개별 뷰를 마스터 또는 슬레이브 복제 모드로 래핑하기 위해 데코레이터를 사용할 수있다.

    django_replicated.decorators에서 가져 오기 use_master, use_slave

    @use_master
    def my_view (request, ...) :
        # master 데이터베이스가 사용되는 동안 모든 db 작업에 사용됩니다.
        # 뷰의 실행 (명시 적으로 오버라이드되지 않은 경우).

    @use_slave
    def my_view (request, ...) :
        # 슬레이브 연결과 동일합니다.


### POST 이후 GET

비동기로 작업 할 때 어드레싱이 필요한 특별한 경우가 있습니다.
복제 구성표. 복제본은 업데이트 수신시 마스터 데이터베이스보다 뒤쳐 질 수 있습니다. 
실제로 이는 업데이트 된 데이터가 포함 된 페이지로 리디렉션되는 POST 양식을 제출 한 후 
아직 업데이트되지 않은 슬레이브 복제본에서이 페이지를 요청할 수 있음을 의미합니다. 
그리고 사용자는 제출이 작동하지 않는다는 인상을 갖게됩니다.

이 문제를 극복하기 위해`ReplicationMiddleware`와 데코레이터는 POST 후에 리다이렉션으로 인한
GET 요청 처리가 명시 적으로 마스터 데이터베이스로 라우팅되는 특별한 기술을 지원합니다.


### 전역 재정의

어떤 경우에는 미들웨어가 선택하는 방법을 재정의해야 할 수도 있습니다
HTTP 요청 메소드에 기반한 목표 데이터베이스. 예를 들어
요청 처리기가 알고있는 경우 특정 POST 요청을 슬레이브로 라우팅합니다.
어떤 쓰기도하지 않습니다. 설정 변수`REPLICATED_VIEWS_OVERRIDES`가 보유하고 있습니다
보기 이름 (urlpatterns 이름) 또는보기 가져 오기 경로 또는 URL 경로의 매핑
데이터베이스 이름 :

    REPLICATED_VIEWS_OVERRIDES = {
        'api-store-event': '노예',
        'app.views.do_smthg': '마스터',
        '/ admin / *': '마스터',
        '/ users /': '노예',
    }


## 변경 로그

### 2.0 이전 버전과 호환되지 않는 변경 사항
* 기본`django_replicated.settings` 파일이 추가되었습니다.
* 일부 설정 변수의 이름이 변경되었습니다.

        DATABASE_SLAVES -> REPLICATED_DATABASE_SLAVES
        DATABASE_DOWNTIME -> REPLICATED_DATABASE_DOWNTIME
* 다른 설정 변수가 삭제되었습니다.

        REPLICATED_SELECT_READ_ONLY
* 라우터 가져 오기 경로가`django_replicated.router.ReplicationRouter`로 변경되었습니다.
*`utils.disable_state_change ()`로 상태 전환을 불가능하게하는 기능이 제거되었습니다.
* 데이터베이스 체커가`dbchecker.py` 모듈로 옮겨졌습니다.
*`db_is_not_read_only` 체크가`db_is_writable`으로 이름이 변경되었습니다.
* 쓰기 전에 상태 검사를 추가했습니다. 기본적으로 사용됩니다.
* 이제는 동일한 마스터 - 슬레이브 db 세트에있는 오브젝트 간의 관계를 허용합니다.


## 유사한 라이브러리들

* [django-multidb-router] (https://github.com/jbalogh/django-multidb-router)
